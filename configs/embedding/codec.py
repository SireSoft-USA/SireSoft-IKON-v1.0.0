class EmbeddingConfigCodec:
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
                "embedding config text must be str"
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
                "embedding config root must be object"
            )

        model = value.get(
            "model",
            {},
        )

        if not isinstance(
            model,
            dict,
        ):
            raise ValueError(
                "model section must be object"
            )

        return EmbeddingConfig(
            mode=value.get(
                "mode",
                "fit",
            ),
            model=(
                EmbeddingModelConfig(
                    dimension=model.get(
                        "dimension",
                        256,
                    ),
                    min_n=model.get(
                        "min_n",
                        1,
                    ),
                    max_n=model.get(
                        "max_n",
                        2,
                    ),
                    use_idf=model.get(
                        "use_idf",
                        True,
                    ),
                    sublinear_tf=(
                        model.get(
                            "sublinear_tf",
                            True,
                        )
                    ),
                    l2_normalize=(
                        model.get(
                            "l2_normalize",
                            True,
                        )
                    ),
                )
            ),
            artifact_path=value.get(
                "artifact_path"
            ),
            persist_after_fit=value.get(
                "persist_after_fit",
                False,
            ),
            expected_dimension=value.get(
                "expected_dimension"
            ),
            metadata=value.get(
                "metadata",
                {},
            ),
        )
