class DatasetsConfigCodec:
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
                "datasets config text must be str"
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
                "datasets config root must be object"
            )

        raw_datasets = value.get(
            "datasets"
        )

        if not isinstance(
            raw_datasets,
            list,
        ) or len(
            raw_datasets
        ) == 0:
            raise ValueError(
                "datasets must be non-empty list"
            )

        datasets = []

        for raw_dataset in raw_datasets:
            if not isinstance(
                raw_dataset,
                dict,
            ):
                raise ValueError(
                    "dataset definition must be object"
                )

            raw_sources = (
                raw_dataset.get(
                    "sources"
                )
            )

            if not isinstance(
                raw_sources,
                list,
            ) or len(
                raw_sources
            ) == 0:
                raise ValueError(
                    "dataset sources must be non-empty list"
                )

            sources = []

            for raw_source in raw_sources:
                if not isinstance(
                    raw_source,
                    dict,
                ):
                    raise ValueError(
                        "dataset source must be object"
                    )

                sources.append(
                    DatasetSourceConfig(
                        path=raw_source.get(
                            "path"
                        ),
                        source_format=(
                            raw_source.get(
                                "format"
                            )
                        ),
                        role=raw_source.get(
                            "role",
                            "data",
                        ),
                        required=(
                            raw_source.get(
                                "required",
                                True,
                            )
                        ),
                        metadata=(
                            raw_source.get(
                                "metadata",
                                {},
                            )
                        ),
                    )
                )

            datasets.append(
                DatasetDefinitionConfig(
                    dataset_id=(
                        raw_dataset.get(
                            "dataset_id"
                        )
                    ),
                    name=raw_dataset.get(
                        "name"
                    ),
                    description=(
                        raw_dataset.get(
                            "description",
                            "",
                        )
                    ),
                    sources=sources,
                    metadata=(
                        raw_dataset.get(
                            "metadata",
                            {},
                        )
                    ),
                    enabled=(
                        raw_dataset.get(
                            "enabled",
                            True,
                        )
                    ),
                )
            )

        return DatasetsConfig(
            datasets=datasets,
            enforce_global_source_uniqueness=(
                value.get(
                    "enforce_global_source_uniqueness",
                    True,
                )
            ),
            capture_immutable_baselines=(
                value.get(
                    "capture_immutable_baselines",
                    False,
                )
            ),
            metadata=value.get(
                "metadata",
                {},
            ),
        )
