class Dropout(Layer):
    """
    Inverted dropout implemented with the handwritten PRNG.

    During evaluation it returns the original Value unchanged.
    """

    def __init__(self, probability=0.1, seed=1337):
        Layer.__init__(self)

        if not isinstance(probability, (int, float)):
            raise TypeError("probability must be numeric")
        if probability < 0.0 or probability >= 1.0:
            raise ValueError("probability must satisfy 0 <= p < 1")

        self.probability = float(probability)
        self.random = RandomGenerator(seed)

    def forward(self, value):
        x = Value.ensure(value)

        if not self.training or self.probability == 0.0:
            return x

        keep_probability = 1.0 - self.probability
        mask_values = []

        i = 0
        while i < x.size:
            if self.random.random() < self.probability:
                mask_values.append(0.0)
            else:
                mask_values.append(1.0 / keep_probability)
            i += 1

        mask = Tensor(
            mask_values,
            [dimension for dimension in x.shape],
        )

        return x * Value(mask, requires_grad=False)
