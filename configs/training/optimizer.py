class OptimizerConfig:
    TYPES = (
        "adamw",
        "sgd",
    )

    def __init__(
        self,
        optimizer_type="adamw",
        learning_rate=0.001,
        weight_decay=0.01,
        beta1=0.9,
        beta2=0.999,
        epsilon=1e-8,
        momentum=0.0,
        dampening=0.0,
        nesterov=False,
    ):
        optimizer_type = str(
            optimizer_type
        ).lower()

        if optimizer_type not in self.TYPES:
            raise ValueError(
                "unsupported optimizer type"
            )

        for field_name, value in (
            (
                "learning_rate",
                learning_rate,
            ),
            (
                "weight_decay",
                weight_decay,
            ),
            (
                "beta1",
                beta1,
            ),
            (
                "beta2",
                beta2,
            ),
            (
                "epsilon",
                epsilon,
            ),
            (
                "momentum",
                momentum,
            ),
            (
                "dampening",
                dampening,
            ),
        ):
            if not isinstance(
                value,
                (int, float),
            ):
                raise TypeError(
                    field_name
                    + " must be numeric"
                )

        learning_rate = float(
            learning_rate
        )
        weight_decay = float(
            weight_decay
        )
        beta1 = float(
            beta1
        )
        beta2 = float(
            beta2
        )
        epsilon = float(
            epsilon
        )
        momentum = float(
            momentum
        )
        dampening = float(
            dampening
        )

        if learning_rate <= 0.0:
            raise ValueError(
                "learning_rate must be > 0"
            )

        if weight_decay < 0.0:
            raise ValueError(
                "weight_decay must be >= 0"
            )

        if (
            beta1 < 0.0
            or beta1 >= 1.0
            or beta2 < 0.0
            or beta2 >= 1.0
        ):
            raise ValueError(
                "AdamW betas must satisfy 0 <= beta < 1"
            )

        if epsilon <= 0.0:
            raise ValueError(
                "epsilon must be > 0"
            )

        if momentum < 0.0:
            raise ValueError(
                "momentum must be >= 0"
            )

        if dampening < 0.0:
            raise ValueError(
                "dampening must be >= 0"
            )

        if (
            optimizer_type == "sgd"
            and nesterov
            and (
                momentum <= 0.0
                or dampening != 0.0
            )
        ):
            raise ValueError(
                "SGD nesterov requires momentum > 0 and dampening == 0"
            )

        self.optimizer_type = (
            optimizer_type
        )
        self.learning_rate = (
            learning_rate
        )
        self.weight_decay = (
            weight_decay
        )
        self.beta1 = beta1
        self.beta2 = beta2
        self.epsilon = epsilon
        self.momentum = momentum
        self.dampening = (
            dampening
        )
        self.nesterov = bool(
            nesterov
        )

    def to_dict(
        self,
    ):
        if (
            self.optimizer_type
            == "adamw"
        ):
            return {
                "type": "adamw",
                "learning_rate": (
                    self.learning_rate
                ),
                "beta1": self.beta1,
                "beta2": self.beta2,
                "epsilon": (
                    self.epsilon
                ),
                "weight_decay": (
                    self.weight_decay
                ),
            }

        return {
            "type": "sgd",
            "learning_rate": (
                self.learning_rate
            ),
            "momentum": (
                self.momentum
            ),
            "dampening": (
                self.dampening
            ),
            "weight_decay": (
                self.weight_decay
            ),
            "nesterov": (
                self.nesterov
            ),
        }
