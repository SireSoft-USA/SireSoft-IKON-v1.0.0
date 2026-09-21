class SGD:
    """
    Stochastic gradient descent with optional momentum, dampening,
    Nesterov acceleration, and decoupled weight decay.

    No framework optimizer code is used. Optimizer state is stored explicitly
    by parameter order so it can later be checkpointed by SireLLM.
    """

    def __init__(
        self,
        parameters,
        learning_rate=0.01,
        momentum=0.0,
        dampening=0.0,
        weight_decay=0.0,
        nesterov=False,
    ):
        self.parameters = self._collect(parameters)

        if not isinstance(learning_rate, (int, float)) or learning_rate <= 0.0:
            raise ValueError("learning_rate must be > 0")
        if not isinstance(momentum, (int, float)) or momentum < 0.0:
            raise ValueError("momentum must be >= 0")
        if not isinstance(dampening, (int, float)) or dampening < 0.0:
            raise ValueError("dampening must be >= 0")
        if not isinstance(weight_decay, (int, float)) or weight_decay < 0.0:
            raise ValueError("weight_decay must be >= 0")

        if nesterov and momentum <= 0.0:
            raise ValueError("Nesterov requires momentum > 0")
        if nesterov and dampening != 0.0:
            raise ValueError("Nesterov requires dampening == 0")

        self.learning_rate = float(learning_rate)
        self.momentum = float(momentum)
        self.dampening = float(dampening)
        self.weight_decay = float(weight_decay)
        self.nesterov = bool(nesterov)

        self.step_count = 0
        self._velocity = []

        index = 0
        while index < len(self.parameters):
            parameter = self.parameters[index]
            self._velocity.append(
                Tensor.zeros([dimension for dimension in parameter.shape])
            )
            index += 1

    def _collect(self, parameters):
        if hasattr(parameters, "parameters") and callable(parameters.parameters):
            parameters = parameters.parameters()

        if not isinstance(parameters, (list, tuple)):
            parameters = list(parameters)

        result = []

        for parameter in parameters:
            if not hasattr(parameter, "data"):
                raise TypeError("optimizer parameter must provide data")
            if not hasattr(parameter, "grad"):
                raise TypeError("optimizer parameter must provide grad")
            result.append(parameter)

        if len(result) == 0:
            raise ValueError("optimizer requires at least one parameter")

        return result

    def zero_grad(self):
        for parameter in self.parameters:
            parameter.zero_grad()
        return self

    def step(self):
        self.step_count += 1

        index = 0

        while index < len(self.parameters):
            parameter = self.parameters[index]

            if not getattr(parameter, "requires_grad", True):
                index += 1
                continue

            gradient = parameter.grad.flatten()
            values = parameter.data.flatten()

            if len(gradient) != len(values):
                raise ValueError("gradient/data size mismatch")

            velocity = self._velocity[index].flatten()

            updated_values = []
            updated_velocity = []

            item = 0

            while item < len(values):
                grad_value = gradient[item]
                parameter_value = values[item]

                if self.weight_decay != 0.0:
                    parameter_value = (
                        parameter_value
                        * (
                            1.0
                            - self.learning_rate
                            * self.weight_decay
                        )
                    )

                if self.momentum != 0.0:
                    velocity_value = (
                        self.momentum * velocity[item]
                        + (1.0 - self.dampening) * grad_value
                    )

                    updated_velocity.append(velocity_value)

                    if self.nesterov:
                        direction = (
                            grad_value
                            + self.momentum * velocity_value
                        )
                    else:
                        direction = velocity_value
                else:
                    direction = grad_value
                    updated_velocity.append(0.0)

                updated_values.append(
                    parameter_value
                    - self.learning_rate * direction
                )

                item += 1

            parameter.set_data(
                Tensor(
                    updated_values,
                    [dimension for dimension in parameter.shape],
                )
            )

            self._velocity[index] = Tensor(
                updated_velocity,
                [dimension for dimension in parameter.shape],
            )

            index += 1

        return self

    def state_dict(self):
        velocities = []

        for velocity in self._velocity:
            velocities.append({
                "shape": list(velocity.shape),
                "data": velocity.flatten(),
            })

        return {
            "type": "SGD",
            "step_count": self.step_count,
            "learning_rate": self.learning_rate,
            "momentum": self.momentum,
            "dampening": self.dampening,
            "weight_decay": self.weight_decay,
            "nesterov": self.nesterov,
            "velocity": velocities,
        }

    def load_state_dict(self, state):
        if not isinstance(state, dict):
            raise TypeError("state must be dict")
        if state.get("type") not in (None, "SGD"):
            raise ValueError("optimizer state type mismatch")

        velocity_rows = state.get("velocity", [])

        if len(velocity_rows) != len(self.parameters):
            raise ValueError("velocity state count mismatch")

        restored = []
        index = 0

        while index < len(velocity_rows):
            row = velocity_rows[index]
            tensor = Tensor(row["data"], row["shape"])

            if tensor.shape != self.parameters[index].shape:
                raise ValueError("velocity shape mismatch")

            restored.append(tensor)
            index += 1

        self._velocity = restored
        self.step_count = int(state.get("step_count", 0))
        return self
