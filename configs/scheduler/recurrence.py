class SchedulerRecurrenceConfig:
    MODES = ("once", "interval")

    def __init__(
        self,
        mode="once",
        interval_seconds=None,
        max_runs=None,
        end_at=None,
        catch_up=False,
    ):
        if mode not in self.MODES:
            raise ValueError("unsupported recurrence mode")

        if mode == "interval":
            if (
                not isinstance(interval_seconds, int)
                or interval_seconds <= 0
            ):
                raise ValueError(
                    "interval_seconds must be positive int for interval mode"
                )
        elif interval_seconds is not None:
            raise ValueError(
                "interval_seconds is only valid for interval mode"
            )

        if max_runs is not None and (
            not isinstance(max_runs, int)
            or max_runs <= 0
        ):
            raise ValueError(
                "max_runs must be positive int or None"
            )

        if end_at is not None and (
            not isinstance(end_at, int)
            or end_at < 0
        ):
            raise ValueError(
                "end_at must be non-negative int or None"
            )

        self.mode = mode
        self.interval_seconds = interval_seconds
        self.max_runs = max_runs
        self.end_at = end_at
        self.catch_up = bool(catch_up)

    def to_rule(self):
        return RecurrenceRule(
            mode=self.mode,
            interval_seconds=self.interval_seconds,
            max_runs=self.max_runs,
            end_at=self.end_at,
            catch_up=self.catch_up,
        )

    def to_dict(self):
        return {
            "mode": self.mode,
            "interval_seconds": self.interval_seconds,
            "max_runs": self.max_runs,
            "end_at": self.end_at,
            "catch_up": self.catch_up,
        }
