class PreprocessingConfigCodec:
    def __init__(
        self,
        parser=None,
    ):
        self.parser = (
            JSONParser()
            if parser is None
            else parser
        )

    def decode_text(self, text):
        if not isinstance(text, str):
            raise TypeError(
                "preprocessing config text must be str"
            )

        return self.from_dict(
            self.parser.parse(text)
        )

    def from_dict(self, value):
        if not isinstance(value, dict):
            raise ValueError(
                "preprocessing config root must be object"
            )

        raw_datasets = value.get(
            "datasets"
        )

        if not isinstance(
            raw_datasets,
            list,
        ) or len(raw_datasets) == 0:
            raise ValueError(
                "datasets must be non-empty list"
            )

        datasets = []

        for raw in raw_datasets:
            if not isinstance(raw, dict):
                raise ValueError(
                    "preprocessing dataset entry must be object"
                )

            datasets.append(
                DatasetPreprocessingConfig(
                    dataset_id=raw.get(
                        "dataset_id"
                    ),
                    sources=raw.get(
                        "sources",
                        {},
                    ),
                    normalize=raw.get(
                        "normalize",
                        True,
                    ),
                    strict=raw.get(
                        "strict",
                        True,
                    ),
                    output_path=raw.get(
                        "output_path"
                    ),
                    enabled=raw.get(
                        "enabled",
                        True,
                    ),
                    metadata=raw.get(
                        "metadata",
                        {},
                    ),
                )
            )

        return PreprocessingConfig(
            datasets=datasets,
            allow_default_sources=value.get(
                "allow_default_sources",
                True,
            ),
            require_canonical_outputs=value.get(
                "require_canonical_outputs",
                False,
            ),
            metadata=value.get(
                "metadata",
                {},
            ),
        )
