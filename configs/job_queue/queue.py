class JobQueueDefinitionConfig:
    def __init__(
        self,
        queue_name,
        default_lease_seconds=30,
        default_max_attempts=3,
        enabled=True,
        metadata=None,
    ):
        if not isinstance(
            queue_name,
            str,
        ) or queue_name == "":
            raise ValueError(
                "queue_name must be non-empty str"
            )

        if (
            not isinstance(
                default_lease_seconds,
                int,
            )
            or default_lease_seconds <= 0
        ):
            raise ValueError(
                "default_lease_seconds must be positive int"
            )

        if (
            not isinstance(
                default_max_attempts,
                int,
            )
            or default_max_attempts <= 0
        ):
            raise ValueError(
                "default_max_attempts must be positive int"
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

        self.queue_name = (
            queue_name
        )
        self.default_lease_seconds = (
            default_lease_seconds
        )
        self.default_max_attempts = (
            default_max_attempts
        )
        self.enabled = bool(
            enabled
        )
        self.metadata = self._copy(
            metadata
        )

    def to_dict(
        self,
    ):
        return {
            "queue_name": (
                self.queue_name
            ),
            "default_lease_seconds": (
                self.default_lease_seconds
            ),
            "default_max_attempts": (
                self.default_max_attempts
            ),
            "enabled": (
                self.enabled
            ),
            "metadata": self._copy(
                self.metadata
            ),
        }

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
