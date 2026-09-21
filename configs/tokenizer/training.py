class TokenizerTrainingConfig:
    def __init__(
        self,
        vocab_size=512,
        min_frequency=2,
        special_tokens=None,
    ):
        if (
            not isinstance(
                vocab_size,
                int,
            )
            or vocab_size < 256
        ):
            raise ValueError(
                "vocab_size must be int >= 256"
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

        if special_tokens is not None:
            if not isinstance(
                special_tokens,
                (list, tuple),
            ):
                raise TypeError(
                    "special_tokens must be list/tuple or None"
                )

            normalized = []
            seen = {}

            for token in special_tokens:
                if (
                    not isinstance(
                        token,
                        str,
                    )
                    or token == ""
                ):
                    raise ValueError(
                        "special token must be non-empty str"
                    )

                if token in seen:
                    raise ValueError(
                        "duplicate special token: "
                        + token
                    )

                seen[token] = True
                normalized.append(
                    token
                )

            special_tokens = normalized

        self.vocab_size = vocab_size
        self.min_frequency = (
            min_frequency
        )
        self.special_tokens = (
            None
            if special_tokens is None
            else list(
                special_tokens
            )
        )

    def effective_special_tokens(
        self,
    ):
        if self.special_tokens is None:
            return list(
                SpecialTokens.DEFAULTS
            )

        return list(
            self.special_tokens
        )

    def to_dict(
        self,
    ):
        return {
            "vocab_size": (
                self.vocab_size
            ),
            "min_frequency": (
                self.min_frequency
            ),
            "special_tokens": (
                None
                if self.special_tokens
                is None
                else list(
                    self.special_tokens
                )
            ),
        }
