class LanguageModel(Layer):
    """
    Decoder-only autoregressive language model.

    Pipeline:
      token IDs
        -> token embeddings
        -> optional sinusoidal positions
        -> decoder stack
        -> vocabulary projection logits

    When position_mode == "rotary", RoPE is applied inside every attention head.
    """

    def __init__(
        self,
        vocab_size,
        d_model,
        num_layers,
        num_heads,
        d_ff,
        max_seq_len=1024,
        dropout=0.0,
        position_mode="rotary",
        padding_idx=None,
        seed=1337,
        name="language_model",
    ):
        Layer.__init__(self)

        if not isinstance(vocab_size, int) or vocab_size <= 0:
            raise ValueError("vocab_size must be positive int")
        if not isinstance(max_seq_len, int) or max_seq_len <= 0:
            raise ValueError("max_seq_len must be positive int")
        if position_mode not in ("rotary", "sinusoidal"):
            raise ValueError(
                "position_mode must be rotary or sinusoidal"
            )

        self.vocab_size = vocab_size
        self.d_model = d_model
        self.max_seq_len = max_seq_len
        self.position_mode = position_mode
        self.name = name

        initializer = Initializers(seed)

        self.token_embedding = self.register_layer(
            "token_embedding",
            Embedding(
                num_embeddings=vocab_size,
                embedding_dim=d_model,
                initializer=initializer,
                padding_idx=padding_idx,
                name=name + ".token_embedding",
            ),
        )

        self.position_encoding = None

        if position_mode == "sinusoidal":
            self.position_encoding = (
                SinusoidalPositionEncoding(
                    d_model=d_model,
                    max_seq_len=max_seq_len,
                )
            )

        self.decoder = self.register_layer(
            "decoder",
            Decoder(
                num_layers=num_layers,
                d_model=d_model,
                num_heads=num_heads,
                d_ff=d_ff,
                dropout=dropout,
                initializer=initializer,
                use_rotary=(
                    position_mode == "rotary"
                ),
                name=name + ".decoder",
            ),
        )

        self.lm_head = self.register_layer(
            "lm_head",
            Linear(
                d_model,
                vocab_size,
                bias=False,
                initializer=initializer,
                name=name + ".lm_head",
            ),
        )

    def __call__(
        self,
        token_ids,
        position_offset=0,
    ):
        return self.forward(
            token_ids,
            position_offset=position_offset,
        )

    def forward(
        self,
        token_ids,
        position_offset=0,
    ):
        sequence_length = self._sequence_length(
            token_ids
        )

        if (
            sequence_length
            + position_offset
            > self.max_seq_len
        ):
            raise ValueError(
                "sequence exceeds configured max_seq_len"
            )

        hidden = self.token_embedding(token_ids)

        if self.position_encoding is not None:
            hidden = self.position_encoding.apply(
                hidden,
                position_offset=position_offset,
            )

        hidden = self.decoder(
            hidden,
            mask=CausalMask(),
            position_offset=position_offset,
        )

        return self.lm_head(hidden)

    def _sequence_length(self, token_ids):
        if isinstance(token_ids, int):
            return 1

        if not isinstance(token_ids, (list, tuple)):
            raise TypeError(
                "token_ids must be int/list/tuple"
            )

        if len(token_ids) == 0:
            return 0

        first = token_ids[0]

        if isinstance(first, int):
            return len(token_ids)

        if isinstance(first, (list, tuple)):
            if len(token_ids) == 0:
                return 0

            expected = len(first)

            for row in token_ids:
                if not isinstance(row, (list, tuple)):
                    raise ValueError(
                        "batched token_ids must be rectangular"
                    )

                if len(row) != expected:
                    raise ValueError(
                        "batched token_ids must be rectangular"
                    )

            return expected

        raise TypeError(
            "token_ids must contain integers"
        )
