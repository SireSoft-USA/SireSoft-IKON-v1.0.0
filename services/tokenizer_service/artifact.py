class TokenizerArtifact:
    """
    Protocol-safe tokenizer state.

    The frozen tokenizer model's raw vocabulary export contains integer dict
    keys, which the service protocol intentionally rejects. This artifact stores
    only what is required to reconstruct the model:
      - ordered special tokens
      - ordered merge operations
      - training configuration
    """

    VERSION = 1

    def __init__(
        self,
        special_tokens,
        merges,
        target_vocab_size,
        min_frequency,
    ):
        if not isinstance(
            special_tokens,
            (list, tuple),
        ):
            raise TypeError(
                "special_tokens must be list/tuple"
            )

        if not isinstance(
            merges,
            (list, tuple),
        ):
            raise TypeError(
                "merges must be list/tuple"
            )

        if (
            not isinstance(
                target_vocab_size,
                int,
            )
            or target_vocab_size < 256
        ):
            raise ValueError(
                "target_vocab_size must be int >= 256"
            )

        if (
            not isinstance(
                min_frequency,
                int,
            )
            or min_frequency <= 0
        ):
            raise ValueError(
                "min_frequency must be positive int"
            )

        self.special_tokens = list(
            special_tokens
        )

        self.merges = []

        for row in merges:
            if not isinstance(row, dict):
                raise TypeError(
                    "merge rows must be dict"
                )

            self.merges.append({
                "left": int(
                    row["left"]
                ),
                "right": int(
                    row["right"]
                ),
                "new_id": int(
                    row["new_id"]
                ),
            })

        self.target_vocab_size = (
            target_vocab_size
        )

        self.min_frequency = (
            min_frequency
        )

    def to_dict(self):
        return {
            "version": self.VERSION,
            "special_tokens": list(
                self.special_tokens
            ),
            "merges": [
                {
                    "left": row["left"],
                    "right": row["right"],
                    "new_id": row["new_id"],
                }
                for row in self.merges
            ],
            "target_vocab_size": (
                self.target_vocab_size
            ),
            "min_frequency": (
                self.min_frequency
            ),
        }

    @classmethod
    def from_dict(
        cls,
        value,
    ):
        if not isinstance(value, dict):
            raise TypeError(
                "tokenizer artifact must be dict"
            )

        version = int(
            value.get(
                "version",
                0,
            )
        )

        if version != cls.VERSION:
            raise ValueError(
                "unsupported tokenizer artifact version"
            )

        return cls(
            special_tokens=value[
                "special_tokens"
            ],
            merges=value[
                "merges"
            ],
            target_vocab_size=int(
                value[
                    "target_vocab_size"
                ]
            ),
            min_frequency=int(
                value[
                    "min_frequency"
                ]
            ),
        )

    @classmethod
    def from_model(
        cls,
        model,
        special_tokens,
        target_vocab_size,
        min_frequency,
    ):
        merge_rows = []

        for left, right, new_id in model.merges:
            merge_rows.append({
                "left": left,
                "right": right,
                "new_id": new_id,
            })

        return cls(
            special_tokens=(
                special_tokens.all()
            ),
            merges=merge_rows,
            target_vocab_size=(
                target_vocab_size
            ),
            min_frequency=(
                min_frequency
            ),
        )

    def rebuild_model(
        self,
        Vocabulary,
        BPEModel,
        SpecialTokens,
    ):
        special_registry = SpecialTokens(
            self.special_tokens
        )

        vocabulary = Vocabulary()
        merges = []

        for row in self.merges:
            new_id = vocabulary.add_merge_token(
                row["left"],
                row["right"],
            )

            if new_id != row["new_id"]:
                raise ValueError(
                    "tokenizer artifact merge ID mismatch"
                )

            merges.append(
                (
                    row["left"],
                    row["right"],
                    new_id,
                )
            )

        vocabulary.finalize_special_tokens(
            special_registry.all()
        )

        return (
            BPEModel(
                vocabulary,
                merges,
            ),
            special_registry,
        )
