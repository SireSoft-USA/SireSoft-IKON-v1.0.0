class AdamW:
    """
    AdamW optimizer implemented from scratch.

    Implements:
      - first/second moment estimates
      - bias correction
      - epsilon stabilization
      - decoupled weight decay
      - optional global gradient-norm clipping
      - explicit serializable optimizer state
    """

    def __init__(
        self,
        parameters,
        learning_rate=0.001,
        beta1=0.9,
        beta2=0.999,
        epsilon=1e-8,
        weight_decay=0.01,
        max_grad_norm=None,
    ):
        self.parameters = self._collect(parameters)

        if not isinstance(learning_rate, (int, float)) or learning_rate <= 0.0:
            raise ValueError("learning_rate must be > 0")

        if not isinstance(beta1, (int, float)) or beta1 < 0.0 or beta1 >= 1.0:
            raise ValueError("beta1 must satisfy 0 <= beta1 < 1")

        if not isinstance(beta2, (int, float)) or beta2 < 0.0 or beta2 >= 1.0:
            raise ValueError("beta2 must satisfy 0 <= beta2 < 1")

        if not isinstance(epsilon, (int, float)) or epsilon <= 0.0:
            raise ValueError("epsilon must be > 0")

        if not isinstance(weight_decay, (int, float)) or weight_decay < 0.0:
            raise ValueError("weight_decay must be >= 0")

        if max_grad_norm is not None:
            if (
                not isinstance(max_grad_norm, (int, float))
                or max_grad_norm <= 0.0
            ):
                raise ValueError("max_grad_norm must be positive or None")

        self.learning_rate = float(learning_rate)
        self.beta1 = float(beta1)
        self.beta2 = float(beta2)
        self.epsilon = float(epsilon)
        self.weight_decay = float(weight_decay)
        self.max_grad_norm = (
            None
            if max_grad_norm is None
            else float(max_grad_norm)
        )

        self.step_count = 0
        self._first_moment = []
        self._second_moment = []

        for parameter in self.parameters:
            shape = [dimension for dimension in parameter.shape]
            self._first_moment.append(Tensor.zeros(shape))
            self._second_moment.append(Tensor.zeros(shape))

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

    def global_grad_norm(self):
        total = 0.0

        for parameter in self.parameters:
            if not getattr(parameter, "requires_grad", True):
                continue

            gradient = parameter.grad.flatten()

            if (
                "GPU_BACKEND" in globals()
                and GPU_BACKEND is not None
                and GPU_BACKEND.enabled()
                and len(gradient) > 0
            ):
                total += GPU_BACKEND.sum_squares(gradient)
            else:
                for value in gradient:
                    total += value * value

        return sqrt(total)

    def _gradient_scale(self):
        if self.max_grad_norm is None:
            return 1.0

        norm = self.global_grad_norm()

        if norm == 0.0 or norm <= self.max_grad_norm:
            return 1.0

        return self.max_grad_norm / norm

    def step(self):
        self.step_count += 1

        scale = self._gradient_scale()

        bias_correction1 = 1.0 - (self.beta1 ** self.step_count)
        bias_correction2 = 1.0 - (self.beta2 ** self.step_count)

        parameter_index = 0

        while parameter_index < len(self.parameters):
            parameter = self.parameters[parameter_index]

            if not getattr(parameter, "requires_grad", True):
                parameter_index += 1
                continue

            values = parameter.data.flatten()
            gradients = parameter.grad.flatten()

            if len(values) != len(gradients):
                raise ValueError("gradient/data size mismatch")

            first = self._first_moment[parameter_index].flatten()
            second = self._second_moment[parameter_index].flatten()

            if (
                "GPU_BACKEND" in globals()
                and GPU_BACKEND is not None
                and GPU_BACKEND.enabled()
                and len(values) > 0
            ):
                updated_values, updated_first, updated_second = GPU_BACKEND.adamw(
                    values,
                    gradients,
                    first,
                    second,
                    self.learning_rate,
                    self.beta1,
                    self.beta2,
                    self.epsilon,
                    self.weight_decay,
                    scale,
                    bias_correction1,
                    bias_correction2,
                )
            else:
                updated_values = []
                updated_first = []
                updated_second = []

                item = 0

                while item < len(values):
                    gradient = gradients[item] * scale

                    first_value = (
                        self.beta1 * first[item]
                        + (1.0 - self.beta1) * gradient
                    )

                    second_value = (
                        self.beta2 * second[item]
                        + (1.0 - self.beta2) * gradient * gradient
                    )

                    first_hat = first_value / bias_correction1
                    second_hat = second_value / bias_correction2

                    update = (
                        first_hat
                        / (
                            sqrt(second_hat)
                            + self.epsilon
                        )
                    )

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

                    parameter_value -= (
                        self.learning_rate * update
                    )

                    updated_values.append(parameter_value)
                    updated_first.append(first_value)
                    updated_second.append(second_value)

                    item += 1

            shape = [dimension for dimension in parameter.shape]

            parameter.set_data(
                Tensor(updated_values, shape)
            )

            self._first_moment[parameter_index] = Tensor(
                updated_first,
                shape,
            )

            self._second_moment[parameter_index] = Tensor(
                updated_second,
                shape,
            )

            parameter_index += 1

        return self

    def state_dict(self):
        first_rows = []
        second_rows = []

        for tensor in self._first_moment:
            first_rows.append({
                "shape": list(tensor.shape),
                "data": tensor.flatten(),
            })

        for tensor in self._second_moment:
            second_rows.append({
                "shape": list(tensor.shape),
                "data": tensor.flatten(),
            })

        return {
            "type": "AdamW",
            "step_count": self.step_count,
            "learning_rate": self.learning_rate,
            "beta1": self.beta1,
            "beta2": self.beta2,
            "epsilon": self.epsilon,
            "weight_decay": self.weight_decay,
            "max_grad_norm": self.max_grad_norm,
            "first_moment": first_rows,
            "second_moment": second_rows,
        }

    def load_state_dict(self, state):
        if not isinstance(state, dict):
            raise TypeError("state must be dict")

        if state.get("type") not in (None, "AdamW"):
            raise ValueError("optimizer state type mismatch")

        first_rows = state.get("first_moment", [])
        second_rows = state.get("second_moment", [])

        if len(first_rows) != len(self.parameters):
            raise ValueError("first moment state count mismatch")

        if len(second_rows) != len(self.parameters):
            raise ValueError("second moment state count mismatch")

        restored_first = []
        restored_second = []

        index = 0

        while index < len(self.parameters):
            first_tensor = Tensor(
                first_rows[index]["data"],
                first_rows[index]["shape"],
            )

            second_tensor = Tensor(
                second_rows[index]["data"],
                second_rows[index]["shape"],
            )

            expected_shape = self.parameters[index].shape

            if first_tensor.shape != expected_shape:
                raise ValueError("first moment shape mismatch")

            if second_tensor.shape != expected_shape:
                raise ValueError("second moment shape mismatch")

            restored_first.append(first_tensor)
            restored_second.append(second_tensor)
            index += 1

        self._first_moment = restored_first
        self._second_moment = restored_second
        self.step_count = int(state.get("step_count", 0))
        return self
