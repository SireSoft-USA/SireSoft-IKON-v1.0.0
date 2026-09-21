class LoggingManager:
    """
    Structured logging manager with redaction, bounded retention, filtering,
    trace/correlation support, and binary archival.
    """

    def __init__(
        self,
        minimum_level="DEBUG",
        max_records=10000,
        sanitizer=None,
        archive=None,
    ):
        self.sanitizer = (
            LogSanitizer()
            if sanitizer is None
            else sanitizer
        )

        self.archive = (
            LogArchive()
            if archive is None
            else archive
        )

        self.sink = (
            MemoryLogSink(
                max_records=(
                    max_records
                )
            )
        )

        self._sequence = 0
        self.set_minimum_level(
            minimum_level
        )

        self.filtered_records = 0

    def set_minimum_level(
        self,
        level,
    ):
        normalized = str(
            level
        ).upper()

        if normalized not in LogRecord.LEVELS:
            raise ValueError(
                "invalid minimum log level"
            )

        self.minimum_level = (
            normalized
        )

        return self.minimum_level

    def log(
        self,
        level,
        message,
        timestamp,
        service=None,
        event=None,
        trace_id=None,
        correlation_id=None,
        fields=None,
    ):
        normalized = str(
            level
        ).upper()

        if normalized not in LogRecord.LEVELS:
            raise ValueError(
                "invalid log level"
            )

        if (
            LogRecord.LEVEL_RANK[
                normalized
            ]
            < LogRecord.LEVEL_RANK[
                self.minimum_level
            ]
        ):
            self.filtered_records += 1

            return {
                "accepted": False,
                "record": None,
                "reason": (
                    "below_minimum_level"
                ),
            }

        sanitized_message = (
            self.sanitizer
            .sanitize_message(
                message
            )
        )

        sanitized_fields = (
            self.sanitizer
            .sanitize_fields(
                fields
            )
        )

        self._sequence += 1

        record = LogRecord(
            sequence=(
                self._sequence
            ),
            level=normalized,
            message=(
                sanitized_message
            ),
            timestamp=timestamp,
            service=service,
            event=event,
            trace_id=trace_id,
            correlation_id=(
                correlation_id
            ),
            fields=(
                sanitized_fields
            ),
        )

        self.sink.write(
            record
        )

        return {
            "accepted": True,
            "record": (
                record.to_dict()
            ),
            "reason": None,
        }

    def debug(
        self,
        message,
        timestamp,
        **kwargs
    ):
        return self.log(
            "DEBUG",
            message,
            timestamp,
            **kwargs
        )

    def info(
        self,
        message,
        timestamp,
        **kwargs
    ):
        return self.log(
            "INFO",
            message,
            timestamp,
            **kwargs
        )

    def warning(
        self,
        message,
        timestamp,
        **kwargs
    ):
        return self.log(
            "WARNING",
            message,
            timestamp,
            **kwargs
        )

    def error(
        self,
        message,
        timestamp,
        **kwargs
    ):
        return self.log(
            "ERROR",
            message,
            timestamp,
            **kwargs
        )

    def critical(
        self,
        message,
        timestamp,
        **kwargs
    ):
        return self.log(
            "CRITICAL",
            message,
            timestamp,
            **kwargs
        )

    def query(
        self,
        minimum_level=None,
        levels=None,
        service=None,
        event=None,
        trace_id=None,
        correlation_id=None,
        start_timestamp=None,
        end_timestamp=None,
        limit=100,
        newest_first=False,
    ):
        if minimum_level is not None:
            minimum_level = str(
                minimum_level
            ).upper()

            if minimum_level not in LogRecord.LEVELS:
                raise ValueError(
                    "invalid query minimum_level"
                )

        allowed_levels = None

        if levels is not None:
            if not isinstance(
                levels,
                (list, tuple),
            ):
                raise TypeError(
                    "levels must be list/tuple or None"
                )

            allowed_levels = []

            for level in levels:
                normalized = str(
                    level
                ).upper()

                if normalized not in LogRecord.LEVELS:
                    raise ValueError(
                        "invalid query level"
                    )

                if normalized not in allowed_levels:
                    allowed_levels.append(
                        normalized
                    )

        if (
            not isinstance(
                limit,
                int,
            )
            or limit <= 0
        ):
            raise ValueError(
                "limit must be positive int"
            )

        records = self.sink.records()

        if newest_first:
            records = list(
                reversed(
                    records
                )
            )

        result = []

        for record in records:
            if minimum_level is not None:
                if (
                    record.rank()
                    < LogRecord.LEVEL_RANK[
                        minimum_level
                    ]
                ):
                    continue

            if (
                allowed_levels is not None
                and record.level
                not in allowed_levels
            ):
                continue

            if (
                service is not None
                and record.service
                != service
            ):
                continue

            if (
                event is not None
                and record.event
                != event
            ):
                continue

            if (
                trace_id is not None
                and record.trace_id
                != trace_id
            ):
                continue

            if (
                correlation_id
                is not None
                and record.correlation_id
                != correlation_id
            ):
                continue

            if (
                start_timestamp
                is not None
                and record.timestamp
                < start_timestamp
            ):
                continue

            if (
                end_timestamp
                is not None
                and record.timestamp
                > end_timestamp
            ):
                continue

            result.append(
                record.to_dict()
            )

            if len(
                result
            ) >= limit:
                break

        return {
            "records": result,
            "count": len(
                result
            ),
            "newest_first": bool(
                newest_first
            ),
        }

    def clear(
        self,
    ):
        return self.sink.clear()

    def save_archive(
        self,
        path,
    ):
        return self.archive.save(
            path,
            self.sink.records(),
        )

    def load_archive(
        self,
        path,
        replace=True,
    ):
        loaded = self.archive.load(
            path
        )

        if replace:
            combined = loaded
        else:
            combined = (
                self.sink.records()
                + loaded
            )

        combined.sort(
            key=(
                lambda record: (
                    record.sequence
                )
            )
        )

        self.sink.replace_records(
            combined
        )

        maximum = 0

        for record in self.sink.records():
            if record.sequence > maximum:
                maximum = record.sequence

        self._sequence = maximum

        return {
            "loaded_records": len(
                loaded
            ),
            "retained_records": len(
                self.sink.records()
            ),
            "replace": bool(
                replace
            ),
        }

    def status(
        self,
    ):
        counts = {
            "DEBUG": 0,
            "INFO": 0,
            "WARNING": 0,
            "ERROR": 0,
            "CRITICAL": 0,
        }

        for record in self.sink.records():
            counts[
                record.level
            ] += 1

        return {
            "ready": True,
            "minimum_level": (
                self.minimum_level
            ),
            "retained_records": len(
                self.sink.records()
            ),
            "max_records": (
                self.sink
                .max_records
            ),
            "evicted_records": (
                self.sink
                .evicted_records
            ),
            "filtered_records": (
                self.filtered_records
            ),
            "next_sequence": (
                self._sequence
                + 1
            ),
            "counts_by_level": counts,
            "sanitization": (
                "structured_key_and_simple_inline_redaction"
            ),
        }
