class SchedulerConfig:
    TYPES = (
        "none",
        "disabled",
        "constant",
        "linear_warmup",
        "cosine",
        "warmup_cosine",
    )

    def __init__(
        self,
        scheduler_type="constant",
        learning_rate=None,
        target_learning_rate=None,
        warmup_steps=0,
        start_learning_rate=0.0,
        max_learning_rate=None,
        min_learning_rate=0.0,
        total_steps=1000,
        decay_steps=None,
    ):
        scheduler_type = str(
            scheduler_type
        ).lower()

        if scheduler_type not in self.TYPES:
            raise ValueError(
                "unsupported scheduler type"
            )

        if not isinstance(
            warmup_steps,
            int,
        ) or warmup_steps < 0:
            raise ValueError(
                "warmup_steps must be non-negative int"
            )

        if not isinstance(
            total_steps,
            int,
        ) or total_steps <= 0:
            raise ValueError(
                "total_steps must be positive int"
            )

        if decay_steps is not None and (
            not isinstance(
                decay_steps,
                int,
            )
            or decay_steps <= 0
        ):
            raise ValueError(
                "decay_steps must be positive int or None"
            )

        for name, value in (
            (
                "learning_rate",
                learning_rate,
            ),
            (
                "target_learning_rate",
                target_learning_rate,
            ),
            (
                "start_learning_rate",
                start_learning_rate,
            ),
            (
                "max_learning_rate",
                max_learning_rate,
            ),
            (
                "min_learning_rate",
                min_learning_rate,
            ),
        ):
            if (
                value is not None
                and not isinstance(
                    value,
                    (int, float),
                )
            ):
                raise TypeError(
                    name
                    + " must be numeric or None"
                )

            if (
                value is not None
                and float(
                    value
                )
                < 0.0
            ):
                raise ValueError(
                    name
                    + " must be >= 0"
                )

        self.scheduler_type = (
            scheduler_type
        )
        self.learning_rate = (
            None
            if learning_rate is None
            else float(
                learning_rate
            )
        )
        self.target_learning_rate = (
            None
            if target_learning_rate
            is None
            else float(
                target_learning_rate
            )
        )
        self.warmup_steps = (
            warmup_steps
        )
        self.start_learning_rate = float(
            start_learning_rate
        )
        self.max_learning_rate = (
            None
            if max_learning_rate
            is None
            else float(
                max_learning_rate
            )
        )
        self.min_learning_rate = float(
            min_learning_rate
        )
        self.total_steps = (
            total_steps
        )
        self.decay_steps = (
            decay_steps
        )

    def to_dict(
        self,
        base_learning_rate=None,
    ):
        kind = (
            self.scheduler_type
        )

        if kind in (
            "none",
            "disabled",
        ):
            return {
                "type": kind,
            }

        if kind == "constant":
            rate = self._fallback(
                self.learning_rate,
                base_learning_rate,
                "constant learning rate",
            )

            return {
                "type": "constant",
                "learning_rate": rate,
            }

        if kind == "linear_warmup":
            target = self._fallback(
                self.target_learning_rate,
                base_learning_rate,
                "target learning rate",
            )

            return {
                "type": (
                    "linear_warmup"
                ),
                "target_learning_rate": (
                    target
                ),
                "warmup_steps": (
                    self.warmup_steps
                ),
                "start_learning_rate": (
                    self.start_learning_rate
                ),
            }

        if kind == "cosine":
            maximum = self._fallback(
                self.max_learning_rate,
                base_learning_rate,
                "maximum learning rate",
            )

            return {
                "type": "cosine",
                "max_learning_rate": (
                    maximum
                ),
                "min_learning_rate": (
                    self.min_learning_rate
                ),
                "total_steps": (
                    self.total_steps
                ),
            }

        maximum = self._fallback(
            self.max_learning_rate,
            base_learning_rate,
            "maximum learning rate",
        )

        return {
            "type": (
                "warmup_cosine"
            ),
            "max_learning_rate": (
                maximum
            ),
            "min_learning_rate": (
                self.min_learning_rate
            ),
            "warmup_steps": (
                self.warmup_steps
            ),
            "decay_steps": (
                self.decay_steps
                if self.decay_steps
                is not None
                else self.total_steps
            ),
            "start_learning_rate": (
                self.start_learning_rate
            ),
        }

    def _fallback(
        self,
        value,
        fallback,
        label,
    ):
        result = (
            fallback
            if value is None
            else value
        )

        if result is None:
            raise ValueError(
                label
                + " is required"
            )

        result = float(
            result
        )

        if result <= 0.0:
            raise ValueError(
                label
                + " must be > 0"
            )

        return result
