class TrainingState:
    def __init__(
        self,
        global_step=0,
        epoch=0,
        tokens_seen=0,
        batches_seen=0,
        best_validation_loss=None,
    ):
        self.global_step = int(global_step)
        self.epoch = int(epoch)
        self.tokens_seen = int(tokens_seen)
        self.batches_seen = int(batches_seen)
        self.best_validation_loss = best_validation_loss

    def to_dict(self):
        return {
            "global_step": self.global_step,
            "epoch": self.epoch,
            "tokens_seen": self.tokens_seen,
            "batches_seen": self.batches_seen,
            "best_validation_loss": self.best_validation_loss,
        }

    def load_dict(self, state):
        if not isinstance(state, dict):
            raise TypeError("training state must be dict")

        self.global_step = int(
            state.get("global_step", 0)
        )
        self.epoch = int(
            state.get("epoch", 0)
        )
        self.tokens_seen = int(
            state.get("tokens_seen", 0)
        )
        self.batches_seen = int(
            state.get("batches_seen", 0)
        )
        self.best_validation_loss = state.get(
            "best_validation_loss"
        )

        return self


class Trainer:
    """
    Connects SireLLM's handwritten model, loss, optimizer, schedule and
    gradient-clipping components into an actual training loop.
    """

    def __init__(
        self,
        model,
        optimizer,
        loss_function,
        scheduler=None,
        gradient_clipper=None,
    ):
        if model is None or not hasattr(model, "forward"):
            raise TypeError("model must provide forward()")
        if optimizer is None or not hasattr(optimizer, "step"):
            raise TypeError("optimizer must provide step()")
        if loss_function is None or not callable(loss_function):
            raise TypeError("loss_function must be callable")

        if scheduler is not None and not hasattr(
            scheduler,
            "apply",
        ):
            raise TypeError("scheduler must provide apply()")

        if gradient_clipper is not None and not hasattr(
            gradient_clipper,
            "clip",
        ):
            raise TypeError(
                "gradient_clipper must provide clip()"
            )

        self.model = model
        self.optimizer = optimizer
        self.loss_function = loss_function
        self.scheduler = scheduler
        self.gradient_clipper = gradient_clipper
        self.state = TrainingState()

    def train_batch(self, batch):
        self._validate_batch(batch)

        self.model.train()
        self.optimizer.zero_grad()

        learning_rate = getattr(
            self.optimizer,
            "learning_rate",
            None,
        )

        if self.scheduler is not None:
            learning_rate = self.scheduler.apply(
                self.optimizer,
                self.state.global_step,
            )

        logits = self.model(
            batch.input_ids
        )

        loss = self.loss_function(
            logits,
            batch.labels,
        )

        loss.backward()

        clip_result = None

        if self.gradient_clipper is not None:
            clip_result = self.gradient_clipper.clip(
                self.model.parameters()
            )

        self.optimizer.step()

        active_targets = self._active_targets(
            batch
        )

        self.state.global_step += 1
        self.state.batches_seen += 1
        self.state.tokens_seen += active_targets

        metrics = {
            "loss": loss.item(),
            "learning_rate": learning_rate,
            "global_step": self.state.global_step,
            "active_targets": active_targets,
        }

        if clip_result is not None:
            metrics["grad_norm_before"] = (
                clip_result.norm_before
            )
            metrics["grad_norm_after"] = (
                clip_result.norm_after
            )
            metrics["grad_scale"] = (
                clip_result.scale
            )

        return metrics

    def train_epoch(self, batches):
        total_weighted_loss = 0.0
        total_targets = 0
        batch_count = 0
        last_learning_rate = getattr(
            self.optimizer,
            "learning_rate",
            None,
        )

        for batch in batches:
            metrics = self.train_batch(batch)
            count = metrics["active_targets"]

            total_weighted_loss += (
                metrics["loss"] * count
            )
            total_targets += count
            batch_count += 1
            last_learning_rate = metrics[
                "learning_rate"
            ]

        if batch_count == 0:
            raise ValueError(
                "train_epoch requires at least one batch"
            )

        self.state.epoch += 1

        if total_targets == 0:
            mean_loss = 0.0
        else:
            mean_loss = (
                total_weighted_loss
                / total_targets
            )

        return {
            "epoch": self.state.epoch,
            "batches": batch_count,
            "active_targets": total_targets,
            "loss": mean_loss,
            "learning_rate": last_learning_rate,
            "global_step": self.state.global_step,
        }

    def record_validation_loss(self, loss):
        if not isinstance(loss, (int, float)):
            raise TypeError("validation loss must be numeric")

        loss = float(loss)
        improved = False

        if (
            self.state.best_validation_loss is None
            or loss < self.state.best_validation_loss
        ):
            self.state.best_validation_loss = loss
            improved = True

        return improved

    def state_dict(self):
        return self.state.to_dict()

    def load_state_dict(self, state):
        self.state.load_dict(state)
        return self

    def _active_targets(self, batch):
        if hasattr(batch, "active_target_count"):
            return int(
                batch.active_target_count()
            )

        total = 0

        for row in batch.labels:
            for target in row:
                if target != -100:
                    total += 1

        return total

    def _validate_batch(self, batch):
        if batch is None:
            raise ValueError("batch is required")
        if not hasattr(batch, "input_ids"):
            raise TypeError("batch must provide input_ids")
        if not hasattr(batch, "labels"):
            raise TypeError("batch must provide labels")
