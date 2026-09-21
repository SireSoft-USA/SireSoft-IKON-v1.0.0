class JobWorkerConfig:
    """
    Runtime worker declaration. handler_key resolves to a callable at startup.
    """

    def __init__(
        self,
        worker_id,
        queue_name,
        handler_key,
        lease_seconds=None,
        retry_delay_seconds=0,
        enabled=True,
        metadata=None,
    ):
        for name, value in (
            (
                "worker_id",
                worker_id,
            ),
            (
                "queue_name",
                queue_name,
            ),
            (
                "handler_key",
                handler_key,
            ),
        ):
            if (
                not isinstance(
                    value,
                    str,
                )
                or value == ""
            ):
                raise ValueError(
                    name
                    + " must be non-empty str"
                )

        if lease_seconds is not None and (
            not isinstance(
                lease_seconds,
                int,
            )
            or lease_seconds <= 0
        ):
            raise ValueError(
                "lease_seconds must be positive int or None"
            )

        if (
            not isinstance(
                retry_delay_seconds,
                int,
            )
            or retry_delay_seconds < 0
        ):
            raise ValueError(
                "retry_delay_seconds must be non-negative int"
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

        self.worker_id = worker_id
        self.queue_name = queue_name
        self.handler_key = (
            handler_key
        )
        self.lease_seconds = (
            lease_seconds
        )
        self.retry_delay_seconds = (
            retry_delay_seconds
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
            "worker_id": (
                self.worker_id
            ),
            "queue_name": (
                self.queue_name
            ),
            "handler_key": (
                self.handler_key
            ),
            "lease_seconds": (
                self.lease_seconds
            ),
            "retry_delay_seconds": (
                self.retry_delay_seconds
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
