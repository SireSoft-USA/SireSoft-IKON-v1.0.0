class TrainingJob:
    VALID_STATUSES = ("ready", "training", "completed", "failed")

    def __init__(
        self,
        job_id,
        config,
        model,
        optimizer,
        scheduler,
        loss_function,
        batch_builder,
        trainer,
        evaluator,
        checkpoint_manager,
    ):
        if not isinstance(job_id, str) or job_id == "":
            raise ValueError("job_id must be non-empty str")
        if not isinstance(config, dict):
            raise TypeError("config must be dict")

        self.job_id = job_id
        self.config = self._copy(config)
        self.model = model
        self.optimizer = optimizer
        self.scheduler = scheduler
        self.loss_function = loss_function
        self.batch_builder = batch_builder
        self.trainer = trainer
        self.evaluator = evaluator
        self.checkpoint_manager = checkpoint_manager
        self.status = "ready"
        self.failure = None
        self.history = []
        self.checkpoints = []

    def begin_training(self):
        if self.status == "completed":
            raise RuntimeError("completed job cannot resume training")
        if self.status == "failed":
            raise RuntimeError("failed job must be restored before training")
        self.status = "training"
        return self

    def end_training(self):
        if self.status == "training":
            self.status = "ready"
        return self

    def complete(self):
        self.status = "completed"
        return self

    def fail(self, message):
        self.status = "failed"
        self.failure = str(message)
        return self

    def restore_ready(self):
        self.status = "ready"
        self.failure = None
        return self

    def record(self, kind, metrics):
        if not isinstance(kind, str) or kind == "":
            raise ValueError("history kind must be non-empty str")
        if not isinstance(metrics, dict):
            raise TypeError("history metrics must be dict")

        self.history.append({
            "index": len(self.history) + 1,
            "kind": kind,
            "metrics": self._copy(metrics),
        })
        return self

    def summary(self):
        return {
            "job_id": self.job_id,
            "status": self.status,
            "failure": self.failure,
            "config": self._copy(self.config),
            "training_state": self._copy(self.trainer.state_dict()),
            "history_count": len(self.history),
            "checkpoint_count": len(self.checkpoints),
            "parameter_count": (
                self.model.parameter_count()
                if hasattr(self.model, "parameter_count")
                else None
            ),
            "optimizer": type(self.optimizer).__name__,
            "scheduler": (
                None
                if self.scheduler is None
                else type(self.scheduler).__name__
            ),
        }

    def _copy(self, value):
        if isinstance(value, dict):
            result = {}
            for key in value:
                result[key] = self._copy(value[key])
            return result
        if isinstance(value, list):
            return [self._copy(item) for item in value]
        if isinstance(value, tuple):
            return [self._copy(item) for item in value]
        return value
