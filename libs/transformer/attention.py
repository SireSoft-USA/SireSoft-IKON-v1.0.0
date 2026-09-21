class ScaledDotProductAttention:
    """
    Scaled dot-product attention with a handwritten softmax and backward pass.

    Shapes:
      Q: [query_seq, dim] or [batch, query_seq, dim]
      K: [key_seq, dim]   or [batch, key_seq, dim]
      V: [key_seq, dim]   or [batch, key_seq, dim]

    The output shape follows Q.
    """

    def __init__(self, causal=False):
        self.causal = bool(causal)
        self.last_weights = None

    def __call__(self, query, key, value, mask=None):
        q = Value.ensure(query)
        k = Value.ensure(key)
        v = Value.ensure(value)

        return self.forward(q, k, v, mask)

    def forward(self, query, key, value, mask=None):
        if query.ndim not in (2, 3):
            raise ValueError("attention query must be rank 2 or 3")
        if key.ndim != query.ndim or value.ndim != query.ndim:
            raise ValueError("Q/K/V ranks must match")

        if query.ndim == 2:
            batch_size = 1
            query_length = query.shape[0]
            key_length = key.shape[0]
            dimension = query.shape[1]

            if key.shape[1] != dimension:
                raise ValueError("Q/K dimensions must match")
            if value.shape[0] != key_length:
                raise ValueError("K/V sequence lengths must match")
            if value.shape[1] != dimension:
                raise ValueError("K/V dimensions must match")

        else:
            batch_size = query.shape[0]
            query_length = query.shape[1]
            key_length = key.shape[1]
            dimension = query.shape[2]

            if key.shape[0] != batch_size:
                raise ValueError("Q/K batch sizes must match")
            if value.shape[0] != batch_size:
                raise ValueError("Q/V batch sizes must match")
            if key.shape[2] != dimension:
                raise ValueError("Q/K dimensions must match")
            if value.shape[1] != key_length:
                raise ValueError("K/V sequence lengths must match")
            if value.shape[2] != dimension:
                raise ValueError("K/V dimensions must match")

        if dimension <= 0:
            raise ValueError("attention dimension must be positive")

        scale = 1.0 / sqrt(float(dimension))

        q_values = query.data.flatten()
        k_values = key.data.flatten()
        v_values = value.data.flatten()

        weights = []
        output = [0.0] * (
            batch_size
            * query_length
            * dimension
        )

        batch = 0

        while batch < batch_size:
            batch_weights = []
            query_index = 0

            while query_index < query_length:
                scores = [0.0] * key_length
                allowed = [False] * key_length
                maximum = None

                key_index = 0

                while key_index < key_length:
                    permitted = self._allowed(
                        query_index,
                        key_index,
                        mask,
                    )

                    allowed[key_index] = permitted

                    if permitted:
                        score = 0.0
                        d = 0

                        while d < dimension:
                            q_index = self._index(
                                batch,
                                query_index,
                                d,
                                query_length,
                                dimension,
                            )

                            k_index = self._index(
                                batch,
                                key_index,
                                d,
                                key_length,
                                dimension,
                            )

                            score += (
                                q_values[q_index]
                                * k_values[k_index]
                            )
                            d += 1

                        score *= scale
                        scores[key_index] = score

                        if maximum is None or score > maximum:
                            maximum = score

                    key_index += 1

                if maximum is None:
                    raise ValueError(
                        "attention mask blocks every key for query "
                        + str(query_index)
                    )

                denominator = 0.0
                exponentials = [0.0] * key_length

                key_index = 0

                while key_index < key_length:
                    if allowed[key_index]:
                        value_exp = exp(
                            scores[key_index] - maximum
                        )
                        exponentials[key_index] = value_exp
                        denominator += value_exp

                    key_index += 1

                row_weights = [0.0] * key_length
                key_index = 0

                while key_index < key_length:
                    if allowed[key_index]:
                        row_weights[key_index] = (
                            exponentials[key_index]
                            / denominator
                        )

                    key_index += 1

                batch_weights.append(row_weights)

                d = 0

                while d < dimension:
                    total = 0.0
                    key_index = 0

                    while key_index < key_length:
                        v_index = self._index(
                            batch,
                            key_index,
                            d,
                            key_length,
                            dimension,
                        )

                        total += (
                            row_weights[key_index]
                            * v_values[v_index]
                        )

                        key_index += 1

                    output_index = self._index(
                        batch,
                        query_index,
                        d,
                        query_length,
                        dimension,
                    )

                    output[output_index] = total
                    d += 1

                query_index += 1

            weights.append(batch_weights)
            batch += 1

        self.last_weights = weights

        if query.ndim == 2:
            output_shape = [
                query_length,
                dimension,
            ]
        else:
            output_shape = [
                batch_size,
                query_length,
                dimension,
            ]

        requires_grad = (
            query.requires_grad
            or key.requires_grad
            or value.requires_grad
        )

        out = Value(
            Tensor(output, output_shape),
            requires_grad=requires_grad,
            _children=[query, key, value],
            _op="scaled_dot_product_attention",
        )

        def _backward():
            upstream = out.grad.flatten()

            d_query = [0.0] * len(q_values)
            d_key = [0.0] * len(k_values)
            d_value = [0.0] * len(v_values)

            batch_index = 0

            while batch_index < batch_size:
                query_position = 0

                while query_position < query_length:
                    row_weights = weights[
                        batch_index
                    ][query_position]

                    d_weights = [0.0] * key_length

                    key_position = 0

                    while key_position < key_length:
                        total = 0.0
                        d = 0

                        while d < dimension:
                            upstream_index = self._index(
                                batch_index,
                                query_position,
                                d,
                                query_length,
                                dimension,
                            )

                            value_index = self._index(
                                batch_index,
                                key_position,
                                d,
                                key_length,
                                dimension,
                            )

                            total += (
                                upstream[upstream_index]
                                * v_values[value_index]
                            )

                            if value.requires_grad:
                                d_value[value_index] += (
                                    row_weights[key_position]
                                    * upstream[upstream_index]
                                )

                            d += 1

                        d_weights[key_position] = total
                        key_position += 1

                    weighted_sum = 0.0
                    key_position = 0

                    while key_position < key_length:
                        weighted_sum += (
                            d_weights[key_position]
                            * row_weights[key_position]
                        )
                        key_position += 1

                    key_position = 0

                    while key_position < key_length:
                        weight = row_weights[key_position]

                        if weight != 0.0:
                            d_score = (
                                weight
                                * (
                                    d_weights[key_position]
                                    - weighted_sum
                                )
                            )

                            d = 0

                            while d < dimension:
                                q_index = self._index(
                                    batch_index,
                                    query_position,
                                    d,
                                    query_length,
                                    dimension,
                                )

                                k_index = self._index(
                                    batch_index,
                                    key_position,
                                    d,
                                    key_length,
                                    dimension,
                                )

                                if query.requires_grad:
                                    d_query[q_index] += (
                                        scale
                                        * d_score
                                        * k_values[k_index]
                                    )

                                if key.requires_grad:
                                    d_key[k_index] += (
                                        scale
                                        * d_score
                                        * q_values[q_index]
                                    )

                                d += 1

                        key_position += 1

                    query_position += 1

                batch_index += 1

            if query.requires_grad:
                query._accumulate(
                    Tensor(
                        d_query,
                        [dimension for dimension in query.shape],
                    )
                )

            if key.requires_grad:
                key._accumulate(
                    Tensor(
                        d_key,
                        [dimension for dimension in key.shape],
                    )
                )

            if value.requires_grad:
                value._accumulate(
                    Tensor(
                        d_value,
                        [dimension for dimension in value.shape],
                    )
                )

        out._backward = _backward
        return out

    def _allowed(self, query_index, key_index, mask):
        if mask is not None:
            if hasattr(mask, "allows"):
                return bool(
                    mask.allows(query_index, key_index)
                )

            if isinstance(mask, (list, tuple)):
                return bool(
                    mask[query_index][key_index]
                )

            raise TypeError(
                "mask must provide allows() or be a matrix"
            )

        if self.causal:
            return key_index <= query_index

        return True

    def _index(
        self,
        batch,
        position,
        dimension_index,
        sequence_length,
        dimension,
    ):
        return (
            (batch * sequence_length + position)
            * dimension
            + dimension_index
        )
