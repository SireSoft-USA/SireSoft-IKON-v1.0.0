class ConstantSchedule:
    """
    Constant learning-rate schedule.

    The schedule is intentionally optimizer-agnostic. Any optimizer exposing a
    numeric ``learning_rate`` attribute can be controlled by it.
    """

    def __init__(self, learning_rate):
        if not isinstance(learning_rate, (int, float)):
            raise TypeError("learning_rate must be numeric")
        if learning_rate < 0.0:
            raise ValueError("learning_rate must be >= 0")

        self.base_learning_rate = float(learning_rate)
        self.last_step = -1

    def learning_rate(self, step):
        self._validate_step(step)
        return self.base_learning_rate

    def apply(self, optimizer, step):
        rate = self.learning_rate(step)
        self._set_optimizer_rate(optimizer, rate)
        self.last_step = step
        return rate

    def state_dict(self):
        return {
            "type": "ConstantSchedule",
            "base_learning_rate": self.base_learning_rate,
            "last_step": self.last_step,
        }

    def load_state_dict(self, state):
        if not isinstance(state, dict):
            raise TypeError("state must be dict")
        if state.get("type") not in (None, "ConstantSchedule"):
            raise ValueError("schedule state type mismatch")

        if "base_learning_rate" in state:
            value = state["base_learning_rate"]
            if not isinstance(value, (int, float)) or value < 0.0:
                raise ValueError("invalid base_learning_rate in state")
            self.base_learning_rate = float(value)

        self.last_step = int(state.get("last_step", -1))
        return self

    def _set_optimizer_rate(self, optimizer, rate):
        if optimizer is None or not hasattr(optimizer, "learning_rate"):
            raise TypeError("optimizer must expose learning_rate")
        optimizer.learning_rate = float(rate)

    def _validate_step(self, step):
        if not isinstance(step, int):
            raise TypeError("step must be int")
        if step < 0:
            raise ValueError("step must be >= 0")
