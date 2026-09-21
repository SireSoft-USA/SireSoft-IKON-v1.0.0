def _schedule_wrap_angle(value):
    two_pi = 2.0 * PI

    while value > PI:
        value -= two_pi

    while value < -PI:
        value += two_pi

    return value


def _schedule_cos(value):
    """
    Cosine using a Taylor series after angle reduction.

    No ``math`` module is used because SireLLM's numerical algorithms are
    intentionally handwritten.
    """
    x = _schedule_wrap_angle(value)
    x2 = x * x
    term = 1.0
    total = 1.0
    n = 1

    while n < 16:
        denominator = (
            (2 * n - 1)
            * (2 * n)
        )

        term *= -x2 / denominator
        total += term
        n += 1

    return total


class CosineDecaySchedule:
    """
    Cosine learning-rate decay.

    step 0            -> max_learning_rate
    step total_steps  -> min_learning_rate
    later steps       -> min_learning_rate
    """

    def __init__(
        self,
        max_learning_rate,
        total_steps,
        min_learning_rate=0.0,
    ):
        if not isinstance(max_learning_rate, (int, float)):
            raise TypeError("max_learning_rate must be numeric")
        if max_learning_rate < 0.0:
            raise ValueError("max_learning_rate must be >= 0")

        if not isinstance(min_learning_rate, (int, float)):
            raise TypeError("min_learning_rate must be numeric")
        if min_learning_rate < 0.0:
            raise ValueError("min_learning_rate must be >= 0")

        if min_learning_rate > max_learning_rate:
            raise ValueError(
                "min_learning_rate cannot exceed max_learning_rate"
            )

        if not isinstance(total_steps, int):
            raise TypeError("total_steps must be int")
        if total_steps <= 0:
            raise ValueError("total_steps must be > 0")

        self.max_learning_rate = float(max_learning_rate)
        self.min_learning_rate = float(min_learning_rate)
        self.total_steps = total_steps
        self.last_step = -1

    def learning_rate(self, step):
        self._validate_step(step)

        if step >= self.total_steps:
            return self.min_learning_rate

        progress = step / float(self.total_steps)
        cosine = _schedule_cos(
            PI * progress
        )

        return (
            self.min_learning_rate
            + 0.5
            * (
                self.max_learning_rate
                - self.min_learning_rate
            )
            * (1.0 + cosine)
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
            "type": "CosineDecaySchedule",
            "max_learning_rate": self.max_learning_rate,
            "min_learning_rate": self.min_learning_rate,
            "total_steps": self.total_steps,
            "last_step": self.last_step,
        }

    def load_state_dict(self, state):
        if not isinstance(state, dict):
            raise TypeError("state must be dict")

        if state.get("type") not in (
            None,
            "CosineDecaySchedule",
        ):
            raise ValueError("schedule state type mismatch")

        max_lr = state.get(
            "max_learning_rate",
            self.max_learning_rate,
        )
        min_lr = state.get(
            "min_learning_rate",
            self.min_learning_rate,
        )
        total_steps = state.get(
            "total_steps",
            self.total_steps,
        )

        if not isinstance(max_lr, (int, float)) or max_lr < 0.0:
            raise ValueError("invalid max_learning_rate")
        if not isinstance(min_lr, (int, float)) or min_lr < 0.0:
            raise ValueError("invalid min_learning_rate")
        if min_lr > max_lr:
            raise ValueError("min learning rate exceeds max")
        if not isinstance(total_steps, int) or total_steps <= 0:
            raise ValueError("invalid total_steps")

        self.max_learning_rate = float(max_lr)
        self.min_learning_rate = float(min_lr)
        self.total_steps = total_steps
        self.last_step = int(state.get("last_step", -1))
        return self

    def _validate_step(self, step):
        if not isinstance(step, int):
            raise TypeError("step must be int")
        if step < 0:
            raise ValueError("step must be >= 0")
