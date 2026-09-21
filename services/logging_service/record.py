class LogRecord:
    LEVELS = (
        "DEBUG",
        "INFO",
        "WARNING",
        "ERROR",
        "CRITICAL",
    )

    LEVEL_RANK = {
        "DEBUG": 10,
        "INFO": 20,
        "WARNING": 30,
        "ERROR": 40,
        "CRITICAL": 50,
    }

    def __init__(
        self,
        sequence,
        level,
        message,
        timestamp,
        service=None,
        event=None,
        trace_id=None,
        correlation_id=None,
        fields=None,
    ):
        if (
            not isinstance(
                sequence,
                int,
            )
            or sequence <= 0
        ):
            raise ValueError(
                "sequence must be positive int"
            )

        normalized_level = str(
            level
        ).upper()

        if normalized_level not in self.LEVELS:
            raise ValueError(
                "invalid log level"
            )

        if not isinstance(
            message,
            str,
        ):
            raise TypeError(
                "message must be str"
            )

        if (
            not isinstance(
                timestamp,
                int,
            )
            or timestamp < 0
        ):
            raise ValueError(
                "timestamp must be non-negative int"
            )

        if service is not None and not isinstance(
            service,
            str,
        ):
            raise TypeError(
                "service must be str or None"
            )

        if event is not None and not isinstance(
            event,
            str,
        ):
            raise TypeError(
                "event must be str or None"
            )

        if trace_id is not None and not isinstance(
            trace_id,
            str,
        ):
            raise TypeError(
                "trace_id must be str or None"
            )

        if correlation_id is not None and not isinstance(
            correlation_id,
            str,
        ):
            raise TypeError(
                "correlation_id must be str or None"
            )

        if fields is None:
            fields = {}

        if not isinstance(
            fields,
            dict,
        ):
            raise TypeError(
                "fields must be dict or None"
            )

        self.sequence = sequence
        self.level = normalized_level
        self.message = message
        self.timestamp = timestamp
        self.service = service
        self.event = event
        self.trace_id = trace_id
        self.correlation_id = (
            correlation_id
        )
        self.fields = self._copy(
            fields
        )

    def rank(
        self,
    ):
        return self.LEVEL_RANK[
            self.level
        ]

    def to_dict(
        self,
    ):
        return {
            "sequence": (
                self.sequence
            ),
            "level": self.level,
            "message": (
                self.message
            ),
            "timestamp": (
                self.timestamp
            ),
            "service": (
                self.service
            ),
            "event": self.event,
            "trace_id": (
                self.trace_id
            ),
            "correlation_id": (
                self.correlation_id
            ),
            "fields": self._copy(
                self.fields
            ),
        }

    @classmethod
    def from_dict(
        cls,
        value,
    ):
        if not isinstance(
            value,
            dict,
        ):
            raise TypeError(
                "log record state must be dict"
            )

        return cls(
            sequence=int(
                value[
                    "sequence"
                ]
            ),
            level=value[
                "level"
            ],
            message=value[
                "message"
            ],
            timestamp=int(
                value[
                    "timestamp"
                ]
            ),
            service=value.get(
                "service"
            ),
            event=value.get(
                "event"
            ),
            trace_id=value.get(
                "trace_id"
            ),
            correlation_id=value.get(
                "correlation_id"
            ),
            fields=value.get(
                "fields",
                {},
            ),
        )

    def _copy(
        self,
        value,
    ):
        if isinstance(
            value,
            dict,
        ):
            result = {}

            for key in value:
                result[
                    key
                ] = self._copy(
                    value[
                        key
                    ]
                )

            return result

        if isinstance(
            value,
            list,
        ):
            return [
                self._copy(
                    item
                )
                for item in value
            ]

        if isinstance(
            value,
            tuple,
        ):
            return [
                self._copy(
                    item
                )
                for item in value
            ]

        return value
