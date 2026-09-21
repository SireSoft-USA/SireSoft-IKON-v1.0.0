class Evaluator:
    """
    Validation/evaluation helper for causal language-model batches.

    Evaluation never calls backward() or optimizer.step(). The model's original
    training/eval mode is restored afterward.
    """

    def __init__(self, model, loss_function):
        if model is None or not hasattr(model, "forward"):
            raise TypeError("model must provide forward()")
        if loss_function is None or not callable(loss_function):
            raise TypeError("loss_function must be callable")

        self.model = model
        self.loss_function = loss_function

    def evaluate_batch(self, batch):
        self._validate_batch(batch)

        was_training = bool(
            getattr(self.model, "training", True)
        )

        self.model.eval()

        logits = self.model(
            batch.input_ids
        )

        loss = self.loss_function(
            logits,
            batch.labels,
        )

        if was_training:
            self.model.train()

        active_targets = self._active_targets(
            batch
        )

        loss_value = loss.item()

        return {
            "loss": loss_value,
            "perplexity": exp(loss_value),
            "active_targets": active_targets,
        }

    def evaluate(self, batches):
        was_training = bool(
            getattr(self.model, "training", True)
        )

        self.model.eval()

        total_weighted_loss = 0.0
        total_targets = 0
        batch_count = 0

        for batch in batches:
            self._validate_batch(batch)

            logits = self.model(
                batch.input_ids
            )

            loss = self.loss_function(
                logits,
                batch.labels,
            )

            count = self._active_targets(
                batch
            )

            total_weighted_loss += (
                loss.item() * count
            )
            total_targets += count
            batch_count += 1

        if was_training:
            self.model.train()

        if batch_count == 0:
            raise ValueError(
                "evaluate requires at least one batch"
            )

        if total_targets == 0:
            raise ValueError(
                "evaluation contains no active targets"
            )

        mean_loss = (
            total_weighted_loss
            / total_targets
        )

        return {
            "loss": mean_loss,
            "perplexity": exp(mean_loss),
            "active_targets": total_targets,
            "batches": batch_count,
        }

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
