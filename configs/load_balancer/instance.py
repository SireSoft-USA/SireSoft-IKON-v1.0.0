class LoadBalancerInstanceConfig:
    """
    Serializable internal service-instance declaration.

    handler_key is resolved against runtime handler objects. No executable
    handler is stored in configuration.
    """

    def __init__(
        self,
        instance_id,
        service_name,
        handler_key,
        max_consecutive_failures=3,
        healthy=True,
        accepting_requests=True,
        enabled=True,
        metadata=None,
    ):
        for name, value in (
            ("instance_id", instance_id),
            ("service_name", service_name),
            ("handler_key", handler_key),
        ):
            if (
                not isinstance(value, str)
                or value == ""
            ):
                raise ValueError(
                    name + " must be non-empty str"
                )

        if (
            not isinstance(
                max_consecutive_failures,
                int,
            )
            or max_consecutive_failures <= 0
        ):
            raise ValueError(
                "max_consecutive_failures must be positive int"
            )

        if metadata is None:
            metadata = {}

        if not isinstance(metadata, dict):
            raise TypeError(
                "metadata must be dict or None"
            )

        self.instance_id = instance_id
        self.service_name = service_name
        self.handler_key = handler_key
        self.max_consecutive_failures = (
            max_consecutive_failures
        )
        self.healthy = bool(healthy)
        self.accepting_requests = bool(
            accepting_requests
        )
        self.enabled = bool(enabled)
        self.metadata = self._copy(metadata)

    def to_dict(self):
        return {
            "instance_id": self.instance_id,
            "service_name": self.service_name,
            "handler_key": self.handler_key,
            "max_consecutive_failures": (
                self.max_consecutive_failures
            ),
            "healthy": self.healthy,
            "accepting_requests": (
                self.accepting_requests
            ),
            "enabled": self.enabled,
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
