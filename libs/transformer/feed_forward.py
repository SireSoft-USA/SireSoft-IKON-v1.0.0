class FeedForward(Layer):
    """
    Transformer MLP:
        Linear(d_model -> d_ff)
        GELU
        Dropout
        Linear(d_ff -> d_model)
        Dropout
    """

    def __init__(
        self,
        d_model,
        d_ff,
        dropout=0.0,
        initializer=None,
        name="ffn",
    ):
        Layer.__init__(self)

        if not isinstance(d_model, int) or d_model <= 0:
            raise ValueError("d_model must be positive int")
        if not isinstance(d_ff, int) or d_ff <= 0:
            raise ValueError("d_ff must be positive int")

        if initializer is None:
            initializer = Initializers(1337)

        self.fc1 = self.register_layer(
            "fc1",
            Linear(
                d_model,
                d_ff,
                initializer=initializer,
                name=name + ".fc1",
            ),
        )

        self.activation = self.register_layer(
            "activation",
            GELU(),
        )

        self.dropout1 = self.register_layer(
            "dropout1",
            Dropout(dropout, seed=4201),
        )

        self.fc2 = self.register_layer(
            "fc2",
            Linear(
                d_ff,
                d_model,
                initializer=initializer,
                name=name + ".fc2",
            ),
        )

        self.dropout2 = self.register_layer(
            "dropout2",
            Dropout(dropout, seed=4202),
        )

    def forward(self, value):
        x = self.fc1(value)
        x = self.activation(x)
        x = self.dropout1(x)
        x = self.fc2(x)
        x = self.dropout2(x)
        return x
