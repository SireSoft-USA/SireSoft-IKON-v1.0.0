class Initializers:
    """
    Handwritten deterministic parameter initializers.
    """

    def __init__(self, seed=1337):
        self.random = RandomGenerator(seed)

    def zeros(self, shape):
        return Tensor.zeros(shape)

    def ones(self, shape):
        return Tensor.ones(shape)

    def uniform(self, shape, low=-0.05, high=0.05):
        count = self._product(shape)
        values = []

        i = 0
        while i < count:
            values.append(self.random.uniform(low, high))
            i += 1

        return Tensor(values, shape)

    def xavier_uniform(self, shape, fan_in=None, fan_out=None):
        if len(shape) < 2 and (fan_in is None or fan_out is None):
            raise ValueError("xavier_uniform requires rank >= 2 or explicit fans")

        if fan_in is None:
            fan_in = shape[-2]
        if fan_out is None:
            fan_out = shape[-1]

        if fan_in <= 0 or fan_out <= 0:
            raise ValueError("fan values must be positive")

        limit = sqrt(6.0 / (fan_in + fan_out))
        return self.uniform(shape, -limit, limit)

    def embedding_uniform(self, vocab_size, embedding_dim):
        if vocab_size <= 0 or embedding_dim <= 0:
            raise ValueError("embedding dimensions must be positive")

        limit = 1.0 / sqrt(float(embedding_dim))
        return self.uniform(
            [vocab_size, embedding_dim],
            -limit,
            limit,
        )

    def kaiming_uniform(self, shape, fan_in=None):
        if len(shape) < 2 and fan_in is None:
            raise ValueError("kaiming_uniform requires rank >= 2 or explicit fan_in")

        if fan_in is None:
            fan_in = shape[-2]

        if fan_in <= 0:
            raise ValueError("fan_in must be positive")

        limit = sqrt(6.0 / fan_in)
        return self.uniform(shape, -limit, limit)

    def _product(self, shape):
        total = 1

        for dimension in shape:
            if not isinstance(dimension, int) or dimension < 0:
                raise ValueError("shape dimensions must be non-negative ints")
            total *= dimension

        return total
