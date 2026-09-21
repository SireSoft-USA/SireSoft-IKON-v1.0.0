class LayerNorm(Layer):
    """
    Layer normalization over the final dimension.

    Forward and backward are implemented directly because the current autograd
    core intentionally supports only full-tensor reductions. This gives the
    Transformer a correct last-axis LayerNorm without adding framework code.
    """

    def __init__(
        self,
        normalized_size,
        epsilon=1e-5,
        affine=True,
        initializer=None,
        name="layer_norm",
    ):
        Layer.__init__(self)

        if not isinstance(normalized_size, int) or normalized_size <= 0:
            raise ValueError("normalized_size must be positive int")
        if not isinstance(epsilon, (int, float)) or epsilon <= 0.0:
            raise ValueError("epsilon must be positive")

        self.normalized_size = normalized_size
        self.epsilon = float(epsilon)
        self.affine = bool(affine)
        self.name = name

        if initializer is None:
            initializer = Initializers(1337)

        if self.affine:
            self.gamma = self.register_parameter(
                "gamma",
                Parameter(
                    initializer.ones([normalized_size]),
                    name + ".gamma",
                ),
            )
            self.beta = self.register_parameter(
                "beta",
                Parameter(
                    initializer.zeros([normalized_size]),
                    name + ".beta",
                ),
            )
        else:
            self.gamma = None
            self.beta = None

    def forward(self, value):
        x = Value.ensure(value)

        if x.ndim == 0:
            raise ValueError("LayerNorm requires at least rank 1")

        if x.shape[-1] != self.normalized_size:
            raise ValueError(
                "LayerNorm expected final dimension "
                + str(self.normalized_size)
            )

        x_values = x.data.flatten()
        width = self.normalized_size
        rows = x.size // width

        output = [0.0] * x.size
        means = [0.0] * rows
        inv_stds = [0.0] * rows
        normalized = [0.0] * x.size

        row = 0
        while row < rows:
            start = row * width

            mean = 0.0
            j = 0
            while j < width:
                mean += x_values[start + j]
                j += 1
            mean /= width

            variance = 0.0
            j = 0
            while j < width:
                delta = x_values[start + j] - mean
                variance += delta * delta
                j += 1
            variance /= width

            inv_std = 1.0 / sqrt(variance + self.epsilon)

            means[row] = mean
            inv_stds[row] = inv_std

            j = 0
            while j < width:
                index = start + j
                xhat = (x_values[index] - mean) * inv_std
                normalized[index] = xhat

                if self.affine:
                    output[index] = (
                        xhat * self.gamma.data[j]
                        + self.beta.data[j]
                    )
                else:
                    output[index] = xhat

                j += 1

            row += 1

        children = [x]

        if self.affine:
            children.append(self.gamma)
            children.append(self.beta)

        requires = x.requires_grad
        if self.affine:
            requires = (
                requires
                or self.gamma.requires_grad
                or self.beta.requires_grad
            )

        out = Value(
            Tensor(output, [dimension for dimension in x.shape]),
            requires_grad=requires,
            _children=children,
            _op="layer_norm",
        )

        def _backward():
            upstream = out.grad.flatten()

            if x.requires_grad:
                dx = [0.0] * x.size

                row_index = 0
                while row_index < rows:
                    start = row_index * width
                    inv_std = inv_stds[row_index]

                    sum_dy = 0.0
                    sum_dy_xhat = 0.0

                    j = 0
                    while j < width:
                        index = start + j
                        dy = upstream[index]

                        if self.affine:
                            dy *= self.gamma.data[j]

                        sum_dy += dy
                        sum_dy_xhat += dy * normalized[index]
                        j += 1

                    j = 0
                    while j < width:
                        index = start + j
                        dy = upstream[index]

                        if self.affine:
                            dy *= self.gamma.data[j]

                        dx[index] = (
                            inv_std
                            / width
                            * (
                                width * dy
                                - sum_dy
                                - normalized[index] * sum_dy_xhat
                            )
                        )

                        j += 1

                    row_index += 1

                x._accumulate(
                    Tensor(dx, [dimension for dimension in x.shape])
                )

            if self.affine and self.gamma.requires_grad:
                dgamma = [0.0] * width

                row_index = 0
                while row_index < rows:
                    start = row_index * width
                    j = 0

                    while j < width:
                        index = start + j
                        dgamma[j] += upstream[index] * normalized[index]
                        j += 1

                    row_index += 1

                self.gamma._accumulate(Tensor(dgamma, [width]))

            if self.affine and self.beta.requires_grad:
                dbeta = [0.0] * width

                row_index = 0
                while row_index < rows:
                    start = row_index * width
                    j = 0

                    while j < width:
                        dbeta[j] += upstream[start + j]
                        j += 1

                    row_index += 1

                self.beta._accumulate(Tensor(dbeta, [width]))

        out._backward = _backward
        return out
