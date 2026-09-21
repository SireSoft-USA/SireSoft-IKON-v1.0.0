class MemoryLogSink:
    """
    Bounded deterministic in-memory log sink.
    """

    def __init__(
        self,
        max_records=10000,
    ):
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

        self.max_records = (
            max_records
        )

        self._records = []
        self.evicted_records = 0

    def write(
        self,
        record,
    ):
        if not isinstance(
            record,
            LogRecord,
        ):
            raise TypeError(
                "record must be LogRecord"
            )

        self._records.append(
            record
        )

        while len(
            self._records
        ) > self.max_records:
            self._records.pop(
                0
            )
            self.evicted_records += 1

        return record

    def records(
        self,
    ):
        return list(
            self._records
        )

    def clear(
        self,
    ):
        count = len(
            self._records
        )

        self._records = []

        return {
            "cleared_records": (
                count
            ),
        }

    def replace_records(
        self,
        records,
    ):
        staged = []

        for record in records:
            if not isinstance(
                record,
                LogRecord,
            ):
                raise TypeError(
                    "records must contain LogRecord"
                )

            staged.append(
                record
            )

        if len(
            staged
        ) > self.max_records:
            staged = staged[
                len(
                    staged
                )
                - self.max_records:
            ]

        self._records = staged

        return self
