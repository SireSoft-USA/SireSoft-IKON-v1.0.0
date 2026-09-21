class TrainingModelConfig:
    """
    Typed decoder-only language-model configuration.
    """

    def __init__(
        self,
        vocab_size,
        d_model=32,
        num_layers=2,
        num_heads=4,
        d_ff=None,
        max_seq_len=128,
        dropout=0.0,
        position_mode="rotary",
        padding_idx=None,
        seed=1337,
    ):
        for field_name, value in (
            ("vocab_size", vocab_size),
            ("d_model", d_model),
            ("num_layers", num_layers),
            ("num_heads", num_heads),
            ("max_seq_len", max_seq_len),
            ("seed", seed),
        ):
            if not isinstance(value, int):
                raise TypeError(
                    field_name
                    + " must be int"
                )

        if vocab_size <= 0:
            raise ValueError(
                "vocab_size must be positive"
            )

        if d_model <= 0:
            raise ValueError(
                "d_model must be positive"
            )

        if num_layers <= 0:
            raise ValueError(
                "num_layers must be positive"
            )

        if num_heads <= 0:
            raise ValueError(
                "num_heads must be positive"
            )

        if d_model % num_heads != 0:
            raise ValueError(
                "d_model must be divisible by num_heads"
            )

        if d_ff is None:
            d_ff = d_model * 4

        if not isinstance(
            d_ff,
            int,
        ) or d_ff <= 0:
            raise ValueError(
                "d_ff must be positive int"
            )

        if max_seq_len <= 0:
            raise ValueError(
                "max_seq_len must be positive"
            )

        if not isinstance(
            dropout,
            (int, float),
        ):
            raise TypeError(
                "dropout must be numeric"
            )

        dropout = float(
            dropout
        )

        if (
            dropout < 0.0
            or dropout >= 1.0
        ):
            raise ValueError(
                "dropout must satisfy 0 <= dropout < 1"
            )

        if position_mode not in (
            "rotary",
            "sinusoidal",
        ):
            raise ValueError(
                "position_mode must be rotary or sinusoidal"
            )

        if padding_idx is not None:
            if not isinstance(
                padding_idx,
                int,
            ):
                raise TypeError(
                    "padding_idx must be int or None"
                )

            if (
                padding_idx < 0
                or padding_idx >= vocab_size
            ):
                raise ValueError(
                    "padding_idx must be within vocabulary"
                )

        self.vocab_size = vocab_size
        self.d_model = d_model
        self.num_layers = num_layers
        self.num_heads = num_heads
        self.d_ff = d_ff
        self.max_seq_len = (
            max_seq_len
        )
        self.dropout = dropout
        self.position_mode = (
            position_mode
        )
        self.padding_idx = (
            padding_idx
        )
        self.seed = seed

    def to_dict(
        self,
    ):
        return {
            "vocab_size": (
                self.vocab_size
            ),
            "d_model": (
                self.d_model
            ),
            "num_layers": (
                self.num_layers
            ),
            "num_heads": (
                self.num_heads
            ),
            "d_ff": self.d_ff,
            "max_seq_len": (
                self.max_seq_len
            ),
            "dropout": (
                self.dropout
            ),
            "position_mode": (
                self.position_mode
            ),
            "padding_idx": (
                self.padding_idx
            ),
            "seed": self.seed,
        }
