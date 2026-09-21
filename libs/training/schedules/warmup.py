class LinearWarmupSchedule:
    """
    Linear learning-rate warmup.

    Semantics:
      step 0                  -> start_learning_rate
      step warmup_steps       -> target_learning_rate
      steps after warmup      -> target_learning_rate

    This explicit boundary makes checkpoint/resume behavior deterministic.
    """

    def __init__(
        self,
        target_learning_rate,
        warmup_steps,
        start_learning_rate=0.0,
    ):
        if not isinstance(target_learning_rate, (int, float)):
            raise TypeError("target_learning_rate must be numeric")
        if target_learning_rate < 0.0:
            raise ValueError("target_learning_rate must be >= 0")

        if not isinstance(start_learning_rate, (int, float)):
            raise TypeError("start_learning_rate must be numeric")
        if start_learning_rate < 0.0:
            raise ValueError("start_learning_rate must be >= 0")

        if not isinstance(warmup_steps, int):
            raise TypeError("warmup_steps must be int")
        if warmup_steps < 0:
            raise ValueError("warmup_steps must be >= 0")

        self.target_learning_rate = float(target_learning_rate)
        self.start_learning_rate = float(start_learning_rate)
        self.warmup_steps = warmup_steps
        self.last_step = -1

    def learning_rate(self, step):
        self._validate_step(step)

        if self.warmup_steps == 0:
            return self.target_learning_rate

        if step >= self.warmup_steps:
            return self.target_learning_rate

        progress = step / float(self.warmup_steps)

        return (
            self.start_learning_rate
            + (
                self.target_learning_rate
                - self.start_learning_rate
            )
            * progress
        )

    def apply(self, optimizer, step):
        rate = self.learning_rate(step)

        if optimizer is None or not hasattr(optimizer, "learning_rate"):
            raise TypeError("optimizer must expose learning_rate")

        optimizer.learning_rate = float(rate)
        self.last_step = step
        return rate

    def state_dict(self):
        return {
            "type": "LinearWarmupSchedule",
            "target_learning_rate": self.target_learning_rate,
            "start_learning_rate": self.start_learning_rate,
            "warmup_steps": self.warmup_steps,
            "last_step": self.last_step,
        }

    def load_state_dict(self, state):
        if not isinstance(state, dict):
            raise TypeError("state must be dict")

        if state.get("type") not in (
            None,
            "LinearWarmupSchedule",
        ):
            raise ValueError("schedule state type mismatch")

        if "target_learning_rate" in state:
            value = state["target_learning_rate"]
            if not isinstance(value, (int, float)) or value < 0.0:
                raise ValueError("invalid target_learning_rate")
            self.target_learning_rate = float(value)

        if "start_learning_rate" in state:
            value = state["start_learning_rate"]
            if not isinstance(value, (int, float)) or value < 0.0:
                raise ValueError("invalid start_learning_rate")
            self.start_learning_rate = float(value)

        if "warmup_steps" in state:
            value = state["warmup_steps"]
            if not isinstance(value, int) or value < 0:
                raise ValueError("invalid warmup_steps")
            self.warmup_steps = value

        self.last_step = int(state.get("last_step", -1))
        return self

    def _validate_step(self, step):
        if not isinstance(step, int):
            raise TypeError("step must be int")
        if step < 0:
            raise ValueError("step must be >= 0")


class WarmupThenSchedule:
    """
    Composes linear warmup with another schedule.

    During warmup, learning rate rises from ``start_learning_rate`` to the
    downstream schedule's rate at its step 0. After warmup, downstream schedule
    step 0 begins exactly once, avoiding skipped or duplicated decay steps.
    """

    def __init__(
        self,
        after_schedule,
        warmup_steps,
        start_learning_rate=0.0,
    ):
        if after_schedule is None or not hasattr(
            after_schedule,
            "learning_rate",
        ):
            raise TypeError(
                "after_schedule must provide learning_rate(step)"
            )

        if not isinstance(warmup_steps, int) or warmup_steps < 0:
            raise ValueError("warmup_steps must be non-negative int")

        if not isinstance(start_learning_rate, (int, float)):
            raise TypeError("start_learning_rate must be numeric")
        if start_learning_rate < 0.0:
            raise ValueError("start_learning_rate must be >= 0")

        self.after_schedule = after_schedule
        self.warmup_steps = warmup_steps
        self.start_learning_rate = float(start_learning_rate)
        self.last_step = -1

    def learning_rate(self, step):
        self._validate_step(step)

        if self.warmup_steps == 0:
            return self.after_schedule.learning_rate(step)

        downstream_start = self.after_schedule.learning_rate(0)

        if step < self.warmup_steps:
            progress = step / float(self.warmup_steps)

            return (
                self.start_learning_rate
                + (
                    downstream_start
                    - self.start_learning_rate
                )
                * progress
            )

        return self.after_schedule.learning_rate(
            step - self.warmup_steps
        )

    def apply(self, optimizer, step):
        rate = self.learning_rate(step)

        if optimizer is None or not hasattr(optimizer, "learning_rate"):
            raise TypeError("optimizer must expose learning_rate")

        optimizer.learning_rate = float(rate)
        self.last_step = step
        return rate

    def state_dict(self):
        state = {
            "type": "WarmupThenSchedule",
            "warmup_steps": self.warmup_steps,
            "start_learning_rate": self.start_learning_rate,
            "last_step": self.last_step,
        }

        if hasattr(self.after_schedule, "state_dict"):
            state["after_schedule"] = (
                self.after_schedule.state_dict()
            )

        return state

    def _validate_step(self, step):
        if not isinstance(step, int):
            raise TypeError("step must be int")
        if step < 0:
            raise ValueError("step must be >= 0")
