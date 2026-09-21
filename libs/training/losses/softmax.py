class Softmax:
    """
    Numerically stable softmax over the final tensor dimension.

    Supports rank >= 1 Values. Forward and backward are handwritten so the
    operation is efficient enough to reuse later for training/inference.
    """

    def __init__(self, temperature=1.0):
        if not isinstance(temperature, (int, float)):
            raise TypeError("temperature must be numeric")
        if temperature <= 0.0:
            raise ValueError("temperature must be > 0")
        self.temperature = float(temperature)

    def __call__(self, value):
        return self.forward(value)

    def forward(self, value):
        x = Value.ensure(value)

        if x.ndim < 1:
            raise ValueError("softmax requires rank >= 1")

        width = x.shape[-1]

        if width <= 0:
            raise ValueError("softmax final dimension must be non-empty")

        rows = x.size // width
        source = x.data.flatten()
        output = [0.0] * x.size

        row = 0

        while row < rows:
            start = row * width

            maximum = source[start] / self.temperature

            j = 1
            while j < width:
                candidate = source[start + j] / self.temperature

                if candidate > maximum:
                    maximum = candidate

                j += 1

            denominator = 0.0
            exponentials = [0.0] * width

            j = 0
            while j < width:
                shifted = (
                    source[start + j] / self.temperature
                    - maximum
                )

                e = exp(shifted)
                exponentials[j] = e
                denominator += e
                j += 1

            j = 0
            while j < width:
                output[start + j] = (
                    exponentials[j] / denominator
                )
                j += 1

            row += 1

        out = Value(
            Tensor(
                output,
                [dimension for dimension in x.shape],
            ),
            requires_grad=x.requires_grad,
            _children=[x],
            _op="softmax",
        )

        def _backward():
            if not x.requires_grad:
                return

            upstream = out.grad.flatten()
            gradient = [0.0] * x.size

            row_index = 0

            while row_index < rows:
                start = row_index * width

                weighted_sum = 0.0
                j = 0

                while j < width:
                    weighted_sum += (
                        upstream[start + j]
                        * output[start + j]
                    )
                    j += 1

                j = 0

                while j < width:
                    probability = output[start + j]

                    gradient[start + j] = (
                        probability
                        * (
                            upstream[start + j]
                            - weighted_sum
                        )
                        / self.temperature
                    )

                    j += 1

                row_index += 1

            x._accumulate(
                Tensor(
                    gradient,
                    [dimension for dimension in x.shape],
                )
            )

        out._backward = _backward
        return out


class LogSoftmax:
    """
    Numerically stable log-softmax over the final dimension.
    """

    def __init__(self, temperature=1.0):
        if not isinstance(temperature, (int, float)):
            raise TypeError("temperature must be numeric")
        if temperature <= 0.0:
            raise ValueError("temperature must be > 0")
        self.temperature = float(temperature)

    def __call__(self, value):
        return self.forward(value)

    def forward(self, value):
        x = Value.ensure(value)

        if x.ndim < 1:
            raise ValueError("log-softmax requires rank >= 1")

        width = x.shape[-1]

        if width <= 0:
            raise ValueError("final dimension must be non-empty")

        rows = x.size // width
        source = x.data.flatten()
        output = [0.0] * x.size
        probabilities = [0.0] * x.size

        row = 0

        while row < rows:
            start = row * width
            maximum = source[start] / self.temperature

            j = 1
            while j < width:
                candidate = source[start + j] / self.temperature
                if candidate > maximum:
                    maximum = candidate
                j += 1

            denominator = 0.0
            exponentials = [0.0] * width

            j = 0
            while j < width:
                shifted = (
                    source[start + j] / self.temperature
                    - maximum
                )
                e = exp(shifted)
                exponentials[j] = e
                denominator += e
                j += 1

            log_denominator = log(denominator)

            j = 0
            while j < width:
                shifted = (
                    source[start + j] / self.temperature
                    - maximum
                )

                output[start + j] = (
                    shifted - log_denominator
                )

                probabilities[start + j] = (
                    exponentials[j] / denominator
                )

                j += 1

            row += 1

        out = Value(
            Tensor(
                output,
                [dimension for dimension in x.shape],
            ),
            requires_grad=x.requires_grad,
            _children=[x],
            _op="log_softmax",
        )

        def _backward():
            if not x.requires_grad:
                return

            upstream = out.grad.flatten()
            gradient = [0.0] * x.size

            row_index = 0

            while row_index < rows:
                start = row_index * width

                upstream_sum = 0.0
                j = 0

                while j < width:
                    upstream_sum += upstream[start + j]
                    j += 1

                j = 0

                while j < width:
                    gradient[start + j] = (
                        upstream[start + j]
                        - probabilities[start + j]
                        * upstream_sum
                    ) / self.temperature

                    j += 1

                row_index += 1

            x._accumulate(
                Tensor(
                    gradient,
                    [dimension for dimension in x.shape],
                )
            )

        out._backward = _backward
        return out
