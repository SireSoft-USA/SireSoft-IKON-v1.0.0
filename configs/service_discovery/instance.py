class DiscoveryInstanceConfig:
    """
    Serializable service-discovery instance declaration.

    local_handler_key is only a runtime lookup key. Callable handlers are never
    serialized into configuration.
    """

    def __init__(
        self,
        instance_id,
        service_name,
        endpoint,
        lease_seconds=60,
        local_handler_key=None,
        max_consecutive_failures=3,
        enabled=True,
        metadata=None,
    ):
        if not isinstance(instance_id, str) or instance_id == "":
            raise ValueError(
                "instance_id must be non-empty str"
            )

        if not isinstance(service_name, str) or service_name == "":
            raise ValueError(
                "service_name must be non-empty str"
            )

        if not isinstance(endpoint, str) or endpoint == "":
            raise ValueError(
                "endpoint must be non-empty str"
            )

        if (
            not isinstance(lease_seconds, int)
            or lease_seconds <= 0
        ):
            raise ValueError(
                "lease_seconds must be positive int"
            )

        if local_handler_key is not None and (
            not isinstance(local_handler_key, str)
            or local_handler_key == ""
        ):
            raise ValueError(
                "local_handler_key must be non-empty str or None"
            )

        if (
            not isinstance(max_consecutive_failures, int)
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
        self.endpoint = endpoint
        self.lease_seconds = lease_seconds
        self.local_handler_key = (
            local_handler_key
        )
        self.max_consecutive_failures = (
            max_consecutive_failures
        )
        self.enabled = bool(enabled)
        self.metadata = self._copy(metadata)

    def local(self):
        return (
            self.local_handler_key
            is not None
        )

    def to_dict(self):
        return {
            "instance_id": self.instance_id,
            "service_name": self.service_name,
            "endpoint": self.endpoint,
            "lease_seconds": self.lease_seconds,
            "local_handler_key": self.local_handler_key,
            "max_consecutive_failures": (
                self.max_consecutive_failures
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
