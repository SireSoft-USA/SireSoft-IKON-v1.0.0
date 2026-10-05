class MultiHeadAttention(Layer):
    """
    Decoder-style multi-head attention.

    Q/K/V/out projections are trainable Linear layers. Head extraction and
    concatenation have handwritten backward passes so gradients flow through
    the complete attention stack.
    """

    def __init__(
        self,
        d_model,
        num_heads,
        causal=True,
        dropout=0.0,
        initializer=None,
        use_rotary=True,
        name="mha",
    ):
        Layer.__init__(self)

        if not isinstance(d_model, int) or d_model <= 0:
            raise ValueError("d_model must be positive int")
        if not isinstance(num_heads, int) or num_heads <= 0:
            raise ValueError("num_heads must be positive int")
        if d_model % num_heads != 0:
            raise ValueError("d_model must be divisible by num_heads")

        self.d_model = d_model
        self.num_heads = num_heads
        self.head_dim = d_model // num_heads
        self.causal = bool(causal)
        self.use_rotary = bool(use_rotary)
        self.name = name

        if self.use_rotary and self.head_dim % 2 != 0:
            raise ValueError(
                "RoPE requires even head_dim; choose compatible d_model/num_heads"
            )

        if initializer is None:
            initializer = Initializers(1337)

        self.q_proj = self.register_layer(
            "q_proj",
            Linear(
                d_model,
                d_model,
                bias=True,
                initializer=initializer,
                name=name + ".q_proj",
            ),
        )

        self.k_proj = self.register_layer(
            "k_proj",
            Linear(
                d_model,
                d_model,
                bias=True,
                initializer=initializer,
                name=name + ".k_proj",
            ),
        )

        self.v_proj = self.register_layer(
            "v_proj",
            Linear(
                d_model,
                d_model,
                bias=True,
                initializer=initializer,
                name=name + ".v_proj",
            ),
        )

        self.out_proj = self.register_layer(
            "out_proj",
            Linear(
                d_model,
                d_model,
                bias=True,
                initializer=initializer,
                name=name + ".out_proj",
            ),
        )

        self.output_dropout = self.register_layer(
            "output_dropout",
            Dropout(dropout, seed=7331),
        )

        self.rotary = None

        if self.use_rotary:
            self.rotary = RotaryEmbedding(
                self.head_dim
            )

        self.last_attention_weights = None

    def __call__(
        self,
        value,
        context=None,
        mask=None,
        position_offset=0,
    ):
        return self.forward(
            value,
            context=context,
            mask=mask,
            position_offset=position_offset,
        )

    def forward(
        self,
        value,
        context=None,
        mask=None,
        position_offset=0,
    ):
        x = Value.ensure(value)

        if x.ndim not in (2, 3):
            raise ValueError(
                "MultiHeadAttention expects rank 2 or rank 3"
            )

        if x.shape[-1] != self.d_model:
            raise ValueError("attention input d_model mismatch")

        if context is None:
            context_value = x
        else:
            context_value = Value.ensure(context)

        if context_value.ndim != x.ndim:
            raise ValueError("context rank must match query rank")

        if context_value.shape[-1] != self.d_model:
            raise ValueError("context d_model mismatch")

        q = self.q_proj(x)
        k = self.k_proj(context_value)
        v = self.v_proj(context_value)

        head_outputs = []
        all_weights = []

        head = 0

        while head < self.num_heads:
            q_head = self._extract_head(q, head)
            k_head = self._extract_head(k, head)
            v_head = self._extract_head(v, head)

            if self.rotary is not None:
                q_head = self.rotary.apply(
                    q_head,
                    position_offset=position_offset,
                )
                k_head = self.rotary.apply(
                    k_head,
                    position_offset=position_offset,
                )

            attention = ScaledDotProductAttention(
                causal=self.causal
            )

            head_output = attention(
                q_head,
                k_head,
                v_head,
                mask=mask,
            )

            head_outputs.append(head_output)
            all_weights.append(attention.last_weights)
            head += 1

        self.last_attention_weights = all_weights

        concatenated = self._concat_heads(
            head_outputs
        )

        projected = self.out_proj(
            concatenated
        )

        return self.output_dropout(projected)

    def _extract_head(self, value, head_index):
        if head_index < 0 or head_index >= self.num_heads:
            raise IndexError("head index out of bounds")

        source = Value.ensure(value)
        source_values = source.data.flatten()

        if source.ndim == 2:
            batch_size = 1
            sequence_length = source.shape[0]
        else:
            batch_size = source.shape[0]
            sequence_length = source.shape[1]

        head_start = head_index * self.head_dim

        if (
            "GPU_BACKEND" in globals()
            and GPU_BACKEND is not None
            and GPU_BACKEND.enabled()
        ):
            output = GPU_BACKEND.extract_head(
                source_values,
                batch_size,
                sequence_length,
                self.d_model,
                head_start,
                self.head_dim,
            )
        else:
            output = []

        if not (
            "GPU_BACKEND" in globals()
            and GPU_BACKEND is not None
            and GPU_BACKEND.enabled()
        ):
            batch = 0
            while batch < batch_size:
                position = 0

                while position < sequence_length:
                    d = 0

                    while d < self.head_dim:
                        source_index = (
                            (batch * sequence_length + position)
                            * self.d_model
                            + head_start
                            + d
                        )

                        output.append(
                            source_values[source_index]
                        )

                        d += 1

                    position += 1

                batch += 1

        if source.ndim == 2:
            shape = [
                sequence_length,
                self.head_dim,
            ]
        else:
            shape = [
                batch_size,
                sequence_length,
                self.head_dim,
            ]

        out = Value(
            Tensor(output, shape),
            requires_grad=source.requires_grad,
            _children=[source],
            _op="extract_attention_head",
        )

        def _backward():
            if not source.requires_grad:
                return

            upstream = out.grad.flatten()
            if (
                "GPU_BACKEND" in globals()
                and GPU_BACKEND is not None
                and GPU_BACKEND.enabled()
            ):
                gradient = GPU_BACKEND.scatter_head(
                    upstream,
                    batch_size,
                    sequence_length,
                    self.d_model,
                    head_start,
                    self.head_dim,
                )
                source._accumulate(
                    Tensor(gradient, [dimension for dimension in source.shape])
                )
                return

            gradient = [0.0] * source.size
            cursor = 0

            batch_index = 0
            while batch_index < batch_size:
                position_index = 0

                while position_index < sequence_length:
                    dimension = 0

                    while dimension < self.head_dim:
                        source_index = (
                            (
                                batch_index
                                * sequence_length
                                + position_index
                            )
                            * self.d_model
                            + head_start
                            + dimension
                        )

                        gradient[source_index] += (
                            upstream[cursor]
                        )

                        cursor += 1
                        dimension += 1

                    position_index += 1

                batch_index += 1

            source._accumulate(
                Tensor(
                    gradient,
                    [dimension for dimension in source.shape],
                )
            )

        out._backward = _backward
        return out

    def _concat_heads(self, heads):
        if not isinstance(heads, list):
            raise TypeError("heads must be list")
        if len(heads) != self.num_heads:
            raise ValueError("incorrect number of heads")

        first = heads[0]

        if first.ndim == 2:
            batch_size = 1
            sequence_length = first.shape[0]
        elif first.ndim == 3:
            batch_size = first.shape[0]
            sequence_length = first.shape[1]
        else:
            raise ValueError("head tensors must be rank 2 or 3")

        use_cuda = (
            "GPU_BACKEND" in globals()
            and GPU_BACKEND is not None
            and GPU_BACKEND.enabled()
        )

        if use_cuda:
            flat_heads = []
            head_index = 0
            while head_index < self.num_heads:
                flat_heads.extend(heads[head_index].data.flatten())
                head_index += 1
            values = GPU_BACKEND.concat_heads(
                flat_heads,
                batch_size,
                sequence_length,
                self.num_heads,
                self.head_dim,
            )
        else:
            values = [0.0] * (
                batch_size
                * sequence_length
                * self.d_model
            )

        if not use_cuda:
            head_index = 0

            while head_index < self.num_heads:
                head = heads[head_index]

                if head.shape[-1] != self.head_dim:
                    raise ValueError("head dimension mismatch")

                head_values = head.data.flatten()
                cursor = 0
                head_start = (
                    head_index
                    * self.head_dim
                )

                batch = 0
                while batch < batch_size:
                    position = 0

                    while position < sequence_length:
                        dimension = 0

                        while dimension < self.head_dim:
                            target_index = (
                                (
                                    batch * sequence_length
                                    + position
                                )
                                * self.d_model
                                + head_start
                                + dimension
                            )

                            values[target_index] = (
                                head_values[cursor]
                            )

                            cursor += 1
                            dimension += 1

                        position += 1

                    batch += 1

                head_index += 1

        if first.ndim == 2:
            output_shape = [
                sequence_length,
                self.d_model,
            ]
        else:
            output_shape = [
                batch_size,
                sequence_length,
                self.d_model,
            ]

        requires_grad = False

        for head in heads:
            if head.requires_grad:
                requires_grad = True
                break

        out = Value(
            Tensor(values, output_shape),
            requires_grad=requires_grad,
            _children=heads,
            _op="concat_attention_heads",
        )

        def _backward():
            upstream = out.grad.flatten()

            if use_cuda:
                head_idx = 0
                while head_idx < self.num_heads:
                    head_value = heads[head_idx]
                    if head_value.requires_grad:
                        gradient = GPU_BACKEND.split_head_grad(
                            upstream,
                            batch_size,
                            sequence_length,
                            self.num_heads,
                            self.head_dim,
                            head_idx,
                        )
                        head_value._accumulate(
                            Tensor(
                                gradient,
                                [dimension for dimension in head_value.shape],
                            )
                        )
                    head_idx += 1
                return

            head_idx = 0

            while head_idx < self.num_heads:
                head_value = heads[head_idx]

                if head_value.requires_grad:
                    gradient = [0.0] * head_value.size
                    cursor = 0
                    head_start = (
                        head_idx
                        * self.head_dim
                    )

                    batch_idx = 0
                    while batch_idx < batch_size:
                        position_idx = 0

                        while position_idx < sequence_length:
                            dimension_idx = 0

                            while dimension_idx < self.head_dim:
                                source_index = (
                                    (
                                        batch_idx
                                        * sequence_length
                                        + position_idx
                                    )
                                    * self.d_model
                                    + head_start
                                    + dimension_idx
                                )

                                gradient[cursor] = (
                                    upstream[source_index]
                                )

                                cursor += 1
                                dimension_idx += 1

                            position_idx += 1

                        batch_idx += 1

                    head_value._accumulate(
                        Tensor(
                            gradient,
                            [
                                dimension
                                for dimension
                                in head_value.shape
                            ],
                        )
                    )

                head_idx += 1

        out._backward = _backward
        return out
