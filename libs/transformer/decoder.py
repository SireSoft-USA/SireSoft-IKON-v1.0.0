class Decoder(Layer):
    """
    Stack of decoder-only Transformer blocks followed by final LayerNorm.
    """

    def __init__(
        self,
        num_layers,
        d_model,
        num_heads,
        d_ff,
        dropout=0.0,
        initializer=None,
        use_rotary=True,
        name="decoder",
    ):
        Layer.__init__(self)

        if not isinstance(num_layers, int) or num_layers <= 0:
            raise ValueError("num_layers must be positive int")

        if initializer is None:
            initializer = Initializers(1337)

        self.num_layers = num_layers
        self.blocks = []

        index = 0

        while index < num_layers:
            block = TransformerBlock(
                d_model=d_model,
                num_heads=num_heads,
                d_ff=d_ff,
                dropout=dropout,
                initializer=initializer,
                use_rotary=use_rotary,
                name=name + ".block_" + str(index),
            )

            self.register_layer(
                "block_" + str(index),
                block,
            )

            self.blocks.append(block)
            index += 1

        self.final_norm = self.register_layer(
            "final_norm",
            LayerNorm(
                d_model,
                initializer=initializer,
                name=name + ".final_norm",
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

        index = 0

        while index < self.num_layers:
            x = self.blocks[index](
                x,
                mask=mask,
                position_offset=position_offset,
            )
            index += 1

        return self.final_norm(x)
