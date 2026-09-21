class Linear(Layer):
    """
    Fully-connected projection over the last tensor dimension.

    Higher-rank inputs are flattened to rank 2, projected, then reshaped back.
    """

    def __init__(
        self,
        in_features,
        out_features,
        bias=True,
        initializer=None,
        name="linear",
    ):
        Layer.__init__(self)

        if not isinstance(in_features, int) or in_features <= 0:
            raise ValueError("in_features must be positive int")
        if not isinstance(out_features, int) or out_features <= 0:
            raise ValueError("out_features must be positive int")

        self.in_features = in_features
        self.out_features = out_features
        self.use_bias = bool(bias)
        self.name = name

        if initializer is None:
            initializer = Initializers(1337)

        weight_data = initializer.xavier_uniform(
            [in_features, out_features]
        )

        self.weight = self.register_parameter(
            "weight",
            Parameter(weight_data, name + ".weight"),
        )

        if self.use_bias:
            self.bias = self.register_parameter(
                "bias",
                Parameter(
                    initializer.zeros([out_features]),
                    name + ".bias",
                ),
            )
        else:
            self.bias = None

    def forward(self, value):
        x = Value.ensure(value)

        if x.ndim == 0:
            raise ValueError("Linear input must have at least one dimension")

        if x.shape[-1] != self.in_features:
            raise ValueError(
                "Linear expected final dimension "
                + str(self.in_features)
                + ", received "
                + str(x.shape[-1])
            )

        original_shape = list(x.shape)

        if x.ndim == 1:
            matrix_input = x.reshape([1, self.in_features])
            output_shape = [self.out_features]
        else:
            rows = 1
            i = 0

            while i < len(original_shape) - 1:
                rows *= original_shape[i]
                i += 1

            matrix_input = x.reshape([rows, self.in_features])
            output_shape = original_shape[:-1] + [self.out_features]

        output = matrix_input @ self.weight

        if self.bias is not None:
            output = output + self.bias

        return output.reshape(output_shape)
