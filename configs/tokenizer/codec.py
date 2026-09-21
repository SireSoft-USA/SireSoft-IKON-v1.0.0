class TokenizerConfigCodec:
    def __init__(
        self,
        parser=None,
    ):
        self.parser = (
            JSONParser()
            if parser is None
            else parser
        )

    def decode_text(
        self,
        text,
    ):
        if not isinstance(
            text,
            str,
        ):
            raise TypeError(
                "tokenizer config text must be str"
            )

        return self.from_dict(
            self.parser.parse(
                text
            )
        )

    def from_dict(
        self,
        value,
    ):
        if not isinstance(
            value,
            dict,
        ):
            raise ValueError(
                "tokenizer config root must be object"
            )

        training = value.get(
            "training",
            {},
        )

        if not isinstance(
            training,
            dict,
        ):
            raise ValueError(
                "training section must be object"
            )

        return TokenizerConfig(
            mode=value.get(
                "mode",
                "train",
            ),
            training=(
                TokenizerTrainingConfig(
                    vocab_size=(
                        training.get(
                            "vocab_size",
                            512,
                        )
                    ),
                    min_frequency=(
                        training.get(
                            "min_frequency",
                            2,
                        )
                    ),
                    special_tokens=(
                        training.get(
                            "special_tokens"
                        )
                    ),
                )
            ),
            artifact_path=value.get(
                "artifact_path"
            ),
            persist_after_train=value.get(
                "persist_after_train",
                False,
            ),
            metadata=value.get(
                "metadata",
                {},
            ),
        )
