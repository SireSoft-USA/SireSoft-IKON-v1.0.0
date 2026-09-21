class MaintenanceState:
    MODES = (
        "normal",
        "draining",
        "maintenance",
    )

    def __init__(
        self,
    ):
        self.mode = "normal"
        self.reason = None
        self.changed_at = None
        self.transition_count = 0

    def transition(
        self,
        mode,
        now,
        reason=None,
    ):
        if mode not in self.MODES:
            raise ValueError(
                "invalid maintenance mode"
            )

        if not isinstance(
            now,
            int,
        ) or now < 0:
            raise ValueError(
                "now must be non-negative int"
            )

        if reason is not None and not isinstance(
            reason,
            str,
        ):
            raise TypeError(
                "reason must be str or None"
            )

        if self.changed_at is not None and now < self.changed_at:
            raise ValueError(
                "maintenance time cannot move backwards"
            )

        if mode == self.mode:
            return self

        self.mode = mode
        self.reason = reason
        self.changed_at = now
        self.transition_count += 1

        return self

    def accepting_requests(
        self,
    ):
        return self.mode == "normal"

    def to_dict(
        self,
    ):
        return {
            "mode": self.mode,
            "reason": self.reason,
            "changed_at": (
                self.changed_at
            ),
            "transition_count": (
                self.transition_count
            ),
            "accepting_requests": (
                self.accepting_requests()
            ),
        }
