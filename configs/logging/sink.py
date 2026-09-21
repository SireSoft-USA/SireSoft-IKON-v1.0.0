class LogSinkConfig:
    """
    Serializable bounded in-memory sink configuration.
    """

    def __init__(
        self,
        sink_id,
        max_records=10000,
        enabled=True,
        metadata=None,
    ):
        if not isinstance(
            sink_id,
            str,
        ) or sink_id == "":
            raise ValueError(
                "sink_id must be non-empty str"
            )

        if (
            not isinstance(
                max_records,
                int,
            )
            or max_records <= 0
        ):
            raise ValueError(
                "max_records must be positive int"
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

        self.sink_id = sink_id
        self.max_records = (
            max_records
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
            "sink_id": self.sink_id,
            "max_records": (
                self.max_records
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
