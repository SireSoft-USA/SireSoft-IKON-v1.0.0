def _rope_wrap_angle(value):
    two_pi = 2.0 * PI

    while value > PI:
        value -= two_pi

    while value < -PI:
        value += two_pi

    return value


def _rope_sin(value):
    x = _rope_wrap_angle(value)
    term = x
    total = x
    x2 = x * x
    n = 1

    while n < 14:
        denominator = (2 * n) * (2 * n + 1)
        term *= -x2 / denominator
        total += term
        n += 1

    return total


def _rope_cos(value):
    x = _rope_wrap_angle(value)
    term = 1.0
    total = 1.0
    x2 = x * x
    n = 1

    while n < 14:
        denominator = (2 * n - 1) * (2 * n)
        term *= -x2 / denominator
        total += term
        n += 1

    return total


class RotaryEmbedding:
    """
    Rotary positional embedding (RoPE) over the final tensor dimension.

    Supports [sequence, head_dim] and [batch, sequence, head_dim]. The backward
    pass applies the transpose of the same 2D rotations.
    """

    def __init__(self, head_dim, base=10000.0):
        if not isinstance(head_dim, int) or head_dim <= 0:
            raise ValueError("head_dim must be positive int")
        if head_dim % 2 != 0:
            raise ValueError("RoPE head_dim must be even")
        if not isinstance(base, (int, float)) or base <= 1.0:
            raise ValueError("base must be > 1")

        self.head_dim = head_dim
        self.base = float(base)

    def apply(self, value, position_offset=0):
        x = Value.ensure(value)

        if x.ndim not in (2, 3):
            raise ValueError("RoPE expects rank 2 or rank 3")
        if x.shape[-1] != self.head_dim:
            raise ValueError("RoPE head dimension mismatch")
        if not isinstance(position_offset, int) or position_offset < 0:
            raise ValueError("position_offset must be non-negative int")

        if x.ndim == 2:
            batch_size = 1
            sequence_length = x.shape[0]
        else:
            batch_size = x.shape[0]
            sequence_length = x.shape[1]

        source = x.data.flatten()
        output = [0.0] * len(source)

        batch = 0
        while batch < batch_size:
            position = 0

            while position < sequence_length:
                absolute_position = position + position_offset
                pair = 0

                while pair < self.head_dim // 2:
                    even_dimension = 2 * pair
                    odd_dimension = even_dimension + 1
                    exponent = (2.0 * pair) / self.head_dim
                    angle = absolute_position / (self.base ** exponent)

                    cosine = _rope_cos(angle)
                    sine = _rope_sin(angle)

                    even_index = self._flat_index(
                        batch,
                        position,
                        even_dimension,
                        sequence_length,
                    )
                    odd_index = self._flat_index(
                        batch,
                        position,
                        odd_dimension,
                        sequence_length,
                    )

                    even_value = source[even_index]
                    odd_value = source[odd_index]

                    output[even_index] = (
                        even_value * cosine
                        - odd_value * sine
                    )

                    output[odd_index] = (
                        even_value * sine
                        + odd_value * cosine
                    )

                    pair += 1

                position += 1

            batch += 1

        out = Value(
            Tensor(output, [dimension for dimension in x.shape]),
            requires_grad=x.requires_grad,
            _children=[x],
            _op="rotary_embedding",
        )

        def _backward():
            if not x.requires_grad:
                return

            upstream = out.grad.flatten()
            gradient = [0.0] * len(source)

            batch_index = 0
            while batch_index < batch_size:
                position_index = 0

                while position_index < sequence_length:
                    absolute_position = position_index + position_offset
                    pair_index = 0

                    while pair_index < self.head_dim // 2:
                        even_dimension = 2 * pair_index
                        odd_dimension = even_dimension + 1

                        exponent = (
                            2.0 * pair_index
                        ) / self.head_dim

                        angle = (
                            absolute_position
                            / (self.base ** exponent)
                        )

                        cosine = _rope_cos(angle)
                        sine = _rope_sin(angle)

                        even_index = self._flat_index(
                            batch_index,
                            position_index,
                            even_dimension,
                            sequence_length,
                        )
                        odd_index = self._flat_index(
                            batch_index,
                            position_index,
                            odd_dimension,
                            sequence_length,
                        )

                        d_even = upstream[even_index]
                        d_odd = upstream[odd_index]

                        gradient[even_index] += (
                            d_even * cosine
                            + d_odd * sine
                        )

                        gradient[odd_index] += (
                            -d_even * sine
                            + d_odd * cosine
                        )

                        pair_index += 1

                    position_index += 1

                batch_index += 1

            x._accumulate(
                Tensor(
                    gradient,
                    [dimension for dimension in x.shape],
                )
            )

        out._backward = _backward
        return out

    def _flat_index(
        self,
        batch,
        position,
        dimension,
        sequence_length,
    ):
        return (
            (batch * sequence_length + position)
            * self.head_dim
            + dimension
        )
