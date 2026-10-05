class Embedding(Layer):
    """
    Trainable token embedding table with a handwritten gather/scatter gradient.
    """

    def __init__(
        self,
        num_embeddings,
        embedding_dim,
        initializer=None,
        padding_idx=None,
        name="embedding",
    ):
        Layer.__init__(self)

        if not isinstance(num_embeddings, int) or num_embeddings <= 0:
            raise ValueError("num_embeddings must be positive int")
        if not isinstance(embedding_dim, int) or embedding_dim <= 0:
            raise ValueError("embedding_dim must be positive int")
        if padding_idx is not None:
            if not isinstance(padding_idx, int):
                raise TypeError("padding_idx must be int or None")
            if padding_idx < 0 or padding_idx >= num_embeddings:
                raise ValueError("padding_idx out of range")

        self.num_embeddings = num_embeddings
        self.embedding_dim = embedding_dim
        self.padding_idx = padding_idx
        self.name = name

        if initializer is None:
            initializer = Initializers(1337)

        data = initializer.embedding_uniform(
            num_embeddings,
            embedding_dim,
        )

        if padding_idx is not None:
            j = 0
            while j < embedding_dim:
                data[padding_idx, j] = 0.0
                j += 1

        self.weight = self.register_parameter(
            "weight",
            Parameter(data, name + ".weight"),
        )

    def forward(self, token_ids):
        flat_ids, prefix_shape = self._flatten_ids(token_ids)

        if (
            "GPU_BACKEND" in globals()
            and GPU_BACKEND is not None
            and GPU_BACKEND.enabled()
        ):
            return self._forward_cuda(flat_ids, prefix_shape)

        output_values = []

        i = 0
        while i < len(flat_ids):
            token_id = flat_ids[i]

            if token_id < 0 or token_id >= self.num_embeddings:
                raise IndexError("embedding token id out of range")

            j = 0
            while j < self.embedding_dim:
                output_values.append(
                    self.weight.data[token_id, j]
                )
                j += 1

            i += 1

        output_shape = prefix_shape + [self.embedding_dim]
        output_tensor = Tensor(output_values, output_shape)

        out = Value(
            output_tensor,
            requires_grad=self.weight.requires_grad,
            _children=[self.weight],
            _op="embedding_gather",
        )

        def _backward():
            if not self.weight.requires_grad:
                return

            gradient = Tensor.zeros(
                [self.num_embeddings, self.embedding_dim]
            )

            upstream = out.grad.flatten()
            cursor = 0
            row_index = 0

            while row_index < len(flat_ids):
                token_id = flat_ids[row_index]

                j = 0
                while j < self.embedding_dim:
                    value = upstream[cursor]

                    if self.padding_idx is None or token_id != self.padding_idx:
                        gradient[token_id, j] = (
                            gradient[token_id, j] + value
                        )

                    cursor += 1
                    j += 1

                row_index += 1

            self.weight._accumulate(gradient)

        out._backward = _backward
        return out

    def _forward_cuda(self, flat_ids, prefix_shape):
        i = 0
        while i < len(flat_ids):
            token_id = flat_ids[i]
            if token_id < 0 or token_id >= self.num_embeddings:
                raise IndexError("embedding token id out of range")
            i += 1

        output_values = GPU_BACKEND.embedding_forward(
            self.weight.data.flatten(),
            flat_ids,
            self.num_embeddings,
            self.embedding_dim,
        )
        output_shape = prefix_shape + [self.embedding_dim]
        out = Value(
            Tensor(output_values, output_shape),
            requires_grad=self.weight.requires_grad,
            _children=[self.weight],
            _op="embedding_gather",
        )

        def _backward():
            if not self.weight.requires_grad:
                return
            padding = self.padding_idx if self.padding_idx is not None else -1
            gradient = GPU_BACKEND.embedding_backward(
                out.grad.flatten(),
                flat_ids,
                self.num_embeddings,
                self.embedding_dim,
                padding,
            )
            self.weight._accumulate(
                Tensor(gradient, [self.num_embeddings, self.embedding_dim])
            )

        out._backward = _backward
        return out

    def _flatten_ids(self, token_ids):
        if isinstance(token_ids, int):
            return [token_ids], []

        if not isinstance(token_ids, (list, tuple)):
            raise TypeError("token_ids must be int/list/tuple")

        flat = []
        shape = self._infer_and_flatten(token_ids, flat)

        return flat, shape

    def _infer_and_flatten(self, data, flat):
        if isinstance(data, int):
            flat.append(data)
            return []

        if not isinstance(data, (list, tuple)):
            raise TypeError("embedding IDs must be integers")

        if len(data) == 0:
            return [0]

        expected_child_shape = None

        for item in data:
            child_shape = self._infer_and_flatten(item, flat)

            if expected_child_shape is None:
                expected_child_shape = child_shape
            elif child_shape != expected_child_shape:
                raise ValueError("ragged token ID structure")

        return [len(data)] + expected_child_shape
