class RecurrenceRule:
    """
    Deterministic recurrence rule.

    Supported modes:
      once      - run once and complete.
      interval  - repeat every interval_seconds.

    max_runs limits total scheduled dispatches. end_at is an inclusive latest
    scheduled time. catch_up=False schedules the next run relative to the
    actual dispatch time; catch_up=True keeps the original cadence.
    """

    MODES = (
        "once",
        "interval",
    )

    def __init__(
        self,
        mode="once",
        interval_seconds=None,
        max_runs=None,
        end_at=None,
        catch_up=False,
    ):
        if mode not in self.MODES:
            raise ValueError(
                "unsupported recurrence mode"
            )

        if mode == "interval":
            if (
                not isinstance(
                    interval_seconds,
                    int,
                )
                or interval_seconds <= 0
            ):
                raise ValueError(
                    "interval_seconds must be positive int for interval mode"
                )
        elif interval_seconds is not None:
            raise ValueError(
                "interval_seconds is only valid for interval mode"
            )

        if max_runs is not None:
            if (
                not isinstance(
                    max_runs,
                    int,
                )
                or max_runs <= 0
            ):
                raise ValueError(
                    "max_runs must be positive int or None"
                )

        if end_at is not None:
            if (
                not isinstance(
                    end_at,
                    int,
                )
                or end_at < 0
            ):
                raise ValueError(
                    "end_at must be non-negative int or None"
                )

        self.mode = mode
        self.interval_seconds = (
            interval_seconds
        )
        self.max_runs = max_runs
        self.end_at = end_at
        self.catch_up = bool(
            catch_up
        )

    def next_run(
        self,
        previous_scheduled_at,
        dispatched_at,
        run_count,
    ):
        if (
            not isinstance(
                previous_scheduled_at,
                int,
            )
            or previous_scheduled_at < 0
        ):
            raise ValueError(
                "previous_scheduled_at must be non-negative int"
            )

        if (
            not isinstance(
                dispatched_at,
                int,
            )
            or dispatched_at < 0
        ):
            raise ValueError(
                "dispatched_at must be non-negative int"
            )

        if (
            not isinstance(
                run_count,
                int,
            )
            or run_count < 0
        ):
            raise ValueError(
                "run_count must be non-negative int"
            )

        if self.max_runs is not None:
            if run_count >= self.max_runs:
                return None

        if self.mode == "once":
            return None

        if self.catch_up:
            candidate = (
                previous_scheduled_at
                + self.interval_seconds
            )
        else:
            candidate = (
                dispatched_at
                + self.interval_seconds
            )

        if (
            self.end_at is not None
            and candidate > self.end_at
        ):
            return None

        return candidate

    def to_dict(
        self,
    ):
        return {
            "mode": self.mode,
            "interval_seconds": (
                self.interval_seconds
            ),
            "max_runs": self.max_runs,
            "end_at": self.end_at,
            "catch_up": self.catch_up,
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
                "recurrence state must be dict"
            )

        return cls(
            mode=value.get(
                "mode",
                "once",
            ),
            interval_seconds=value.get(
                "interval_seconds"
            ),
            max_runs=value.get(
                "max_runs"
            ),
            end_at=value.get(
                "end_at"
            ),
            catch_up=value.get(
                "catch_up",
                False,
            ),
        )
