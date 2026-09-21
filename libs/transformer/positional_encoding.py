def _pe_wrap_angle(value):
    two_pi = 2.0 * PI

    while value > PI:
        value -= two_pi

    while value < -PI:
        value += two_pi

    return value


def _pe_sin(value):
    x = _pe_wrap_angle(value)
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


def _pe_cos(value):
    x = _pe_wrap_angle(value)
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


class SinusoidalPositionEncoding:
    """
    Classic fixed sinusoidal positional encoding.

    The encoding is created using handwritten trigonometric approximations.
    It is non-trainable and is added as a constant Value, so gradients pass
    directly back to the input embeddings.
    """

    def __init__(self, d_model, max_seq_len=4096, base=10000.0):
        if not isinstance(d_model, int) or d_model <= 0:
            raise ValueError("d_model must be positive int")
        if not isinstance(max_seq_len, int) or max_seq_len <= 0:
            raise ValueError("max_seq_len must be positive int")
        if not isinstance(base, (int, float)) or base <= 1.0:
            raise ValueError("base must be > 1")

        self.d_model = d_model
        self.max_seq_len = max_seq_len
        self.base = float(base)

    def encoding(self, sequence_length, batch_size=None, position_offset=0):
        if not isinstance(sequence_length, int) or sequence_length < 0:
            raise ValueError("sequence_length must be non-negative int")
        if sequence_length + position_offset > self.max_seq_len:
            raise ValueError("requested positions exceed max_seq_len")
        if position_offset < 0:
            raise ValueError("position_offset must be >= 0")

        one_sequence = []

        position = 0
        while position < sequence_length:
            absolute_position = position + position_offset
            dimension = 0

            while dimension < self.d_model:
                pair_index = dimension // 2
                exponent = (2.0 * pair_index) / self.d_model
                denominator = self.base ** exponent
                angle = absolute_position / denominator

                if dimension % 2 == 0:
                    one_sequence.append(_pe_sin(angle))
                else:
                    one_sequence.append(_pe_cos(angle))

                dimension += 1

            position += 1

        if batch_size is None:
            return Tensor(one_sequence, [sequence_length, self.d_model])

        if not isinstance(batch_size, int) or batch_size <= 0:
            raise ValueError("batch_size must be positive int")

        values = []
        batch = 0

        while batch < batch_size:
            for value in one_sequence:
                values.append(value)
            batch += 1

        return Tensor(
            values,
            [batch_size, sequence_length, self.d_model],
        )

    def apply(self, value, position_offset=0):
        x = Value.ensure(value)

        if x.ndim == 2:
            sequence_length = x.shape[0]
            if x.shape[1] != self.d_model:
                raise ValueError("position encoding d_model mismatch")

            encoding = self.encoding(
                sequence_length,
                position_offset=position_offset,
            )

        elif x.ndim == 3:
            batch_size = x.shape[0]
            sequence_length = x.shape[1]

            if x.shape[2] != self.d_model:
                raise ValueError("position encoding d_model mismatch")

            encoding = self.encoding(
                sequence_length,
                batch_size=batch_size,
                position_offset=position_offset,
            )

        else:
            raise ValueError(
                "SinusoidalPositionEncoding expects rank 2 or rank 3"
            )

        return x + Value(
            encoding,
            requires_grad=False,
            label="position_encoding",
        )
