class TrainingJobConfig:
    """
    Complete typed training-job configuration.
    """

    def __init__(
        self,
        model,
        optimizer=None,
        scheduler=None,
        training=None,
        metadata=None,
    ):
        if not isinstance(
            model,
            TrainingModelConfig,
        ):
            raise TypeError(
                "model must be TrainingModelConfig"
            )

        if optimizer is None:
            optimizer = (
                OptimizerConfig()
            )

        if not isinstance(
            optimizer,
            OptimizerConfig,
        ):
            raise TypeError(
                "optimizer must be OptimizerConfig or None"
            )

        if scheduler is None:
            scheduler = (
                SchedulerConfig()
            )

        if not isinstance(
            scheduler,
            SchedulerConfig,
        ):
            raise TypeError(
                "scheduler must be SchedulerConfig or None"
            )

        if training is None:
            training = (
                TrainingLoopConfig()
            )

        if not isinstance(
            training,
            TrainingLoopConfig,
        ):
            raise TypeError(
                "training must be TrainingLoopConfig or None"
            )

        if metadata is None:
            metadata = {}

        if not isinstance(
            metadata,
            dict,
        ):
            raise TypeError(
                "metadata must be dict or None"
            )

        self.model = model
        self.optimizer = optimizer
        self.scheduler = scheduler
        self.training = training
        self.metadata = self._copy(
            metadata
        )

    def to_factory_dict(
        self,
    ):
        return {
            "model": (
                self.model.to_dict()
            ),
            "optimizer": (
                self.optimizer.to_dict()
            ),
            "scheduler": (
                self.scheduler.to_dict(
                    base_learning_rate=(
                        self.optimizer
                        .learning_rate
                    )
                )
            ),
            "training": (
                self.training.to_dict()
            ),
        }

    def to_dict(
        self,
    ):
        result = (
            self.to_factory_dict()
        )

        result[
            "metadata"
        ] = self._copy(
            self.metadata
        )

        return result

    def _copy(
        self,
        value,
    ):
        if isinstance(
            value,
            dict,
        ):
            return {
                key: self._copy(
                    value[
                        key
                    ]
                )
                for key
                in value
            }

        if isinstance(
            value,
            (list, tuple),
        ):
            return [
                self._copy(
                    item
                )
                for item
                in value
            ]

        return value
