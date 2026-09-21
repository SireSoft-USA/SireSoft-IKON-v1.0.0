class LoadBalancerConfig:
    STRATEGIES = (
        "round_robin",
        "least_load",
        "adaptive",
    )

    def __init__(
        self,
        strategy="adaptive",
        max_attempts=2,
        instances=None,
        require_service_redundancy=False,
        metadata=None,
    ):
        if strategy not in self.STRATEGIES:
            raise ValueError(
                "unsupported load-balancer strategy"
            )

        if (
            not isinstance(max_attempts, int)
            or max_attempts <= 0
        ):
            raise ValueError(
                "max_attempts must be positive int"
            )

        if instances is None:
            instances = []

        if not isinstance(
            instances,
            (list, tuple),
        ):
            raise TypeError(
                "instances must be list/tuple or None"
            )

        normalized = []
        seen = {}

        for instance in instances:
            if not isinstance(
                instance,
                LoadBalancerInstanceConfig,
            ):
                raise TypeError(
                    "instance entries must be LoadBalancerInstanceConfig"
                )

            if instance.instance_id in seen:
                raise ValueError(
                    "duplicate load-balancer instance_id: "
                    + instance.instance_id
                )

            seen[instance.instance_id] = True
            normalized.append(instance)

        if metadata is None:
            metadata = {}

        if not isinstance(metadata, dict):
            raise TypeError(
                "metadata must be dict or None"
            )

        self.strategy = strategy
        self.max_attempts = max_attempts
        self.instances = normalized
        self.require_service_redundancy = bool(
            require_service_redundancy
        )
        self.metadata = self._copy(metadata)

    def enabled_instances(self):
        return [
            item
            for item in self.instances
            if item.enabled
        ]

    def to_dict(self):
        return {
            "strategy": self.strategy,
            "max_attempts": self.max_attempts,
            "instances": [
                item.to_dict()
                for item in self.instances
            ],
            "require_service_redundancy": (
                self.require_service_redundancy
            ),
            "metadata": self._copy(
                self.metadata
            ),
        }

    def _copy(self, value):
        if isinstance(value, dict):
            return {
                key: self._copy(value[key])
                for key in value
            }

        if isinstance(value, (list, tuple)):
            return [
                self._copy(item)
                for item in value
            ]

        return value
