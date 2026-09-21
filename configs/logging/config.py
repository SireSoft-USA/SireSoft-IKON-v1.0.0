class LoggingConfig:
    """
    Logging-service configuration.

    Current LoggingManager owns one bounded memory sink, so exactly one enabled
    sink is selected by the factory. Additional disabled sink definitions can
    be retained for deployment planning without changing runtime behavior.
    """

    def __init__(
        self,
        minimum_level="INFO",
        sinks=None,
        archive_path=None,
        metadata=None,
    ):
        normalized_level = str(
            minimum_level
        ).upper()

        if normalized_level not in (
            "DEBUG",
            "INFO",
            "WARNING",
            "ERROR",
            "CRITICAL",
        ):
            raise ValueError(
                "invalid minimum log level"
            )

        if sinks is None:
            sinks = [
                LogSinkConfig(
                    "memory"
                ),
            ]

        if not isinstance(
            sinks,
            (list, tuple),
        ) or len(
            sinks
        ) == 0:
            raise ValueError(
                "sinks must be non-empty list/tuple"
            )

        normalized_sinks = []
        seen = {}

        for sink in sinks:
            if not isinstance(
                sink,
                LogSinkConfig,
            ):
                raise TypeError(
                    "sinks entries must be LogSinkConfig"
                )

            if sink.sink_id in seen:
                raise ValueError(
                    "duplicate sink_id: "
                    + sink.sink_id
                )

            seen[
                sink.sink_id
            ] = True
            normalized_sinks.append(
                sink
            )

        if archive_path is not None and (
            not isinstance(
                archive_path,
                str,
            )
            or archive_path == ""
        ):
            raise ValueError(
                "archive_path must be non-empty str or None"
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

        self.minimum_level = (
            normalized_level
        )
        self.sinks = normalized_sinks
        self.archive_path = (
            archive_path
        )
        self.metadata = self._copy(
            metadata
        )

    def enabled_sinks(
        self,
    ):
        return [
            sink
            for sink
            in self.sinks
            if sink.enabled
        ]

    def to_dict(
        self,
    ):
        return {
            "minimum_level": (
                self.minimum_level
            ),
            "sinks": [
                sink.to_dict()
                for sink
                in self.sinks
            ],
            "archive_path": (
                self.archive_path
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
