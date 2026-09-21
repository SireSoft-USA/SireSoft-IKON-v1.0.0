class TransformerBlock(Layer):
    """
    Pre-normalization decoder Transformer block.
    """

    def __init__(
        self,
        d_model,
        num_heads,
        d_ff,
        dropout=0.0,
        initializer=None,
        use_rotary=True,
        name="block",
    ):
        Layer.__init__(self)

        if initializer is None:
            initializer = Initializers(1337)

        self.norm1 = self.register_layer(
            "norm1",
            LayerNorm(
                d_model,
                initializer=initializer,
                name=name + ".norm1",
            ),
        )

        self.attention = self.register_layer(
            "attention",
            MultiHeadAttention(
                d_model=d_model,
                num_heads=num_heads,
                causal=True,
                dropout=dropout,
                initializer=initializer,
                use_rotary=use_rotary,
                name=name + ".attention",
            ),
        )

        self.norm2 = self.register_layer(
            "norm2",
            LayerNorm(
                d_model,
                initializer=initializer,
                name=name + ".norm2",
            ),
        )

        self.feed_forward = self.register_layer(
            "feed_forward",
            FeedForward(
                d_model=d_model,
                d_ff=d_ff,
                dropout=dropout,
                initializer=initializer,
                name=name + ".ffn",
            ),
        )

    def __call__(
        self,
        value,
        mask=None,
        position_offset=0,
    ):
        return self.forward(
            value,
            mask=mask,
            position_offset=position_offset,
        )

    def forward(
        self,
        value,
        mask=None,
        position_offset=0,
    ):
        x = Value.ensure(value)

        attention_input = self.norm1(x)

        attention_output = self.attention(
            attention_input,
            mask=mask,
            position_offset=position_offset,
        )

        x = x + attention_output

        feed_forward_input = self.norm2(x)
        feed_forward_output = self.feed_forward(
            feed_forward_input
        )

        return x + feed_forward_output
