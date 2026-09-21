class DatasetDefinitionConfig:
    """
    Serializable dataset-family definition.
    """

    def __init__(
        self,
        dataset_id,
        name,
        sources,
        description="",
        metadata=None,
        enabled=True,
    ):
        if not isinstance(
            dataset_id,
            str,
        ) or dataset_id == "":
            raise ValueError(
                "dataset_id must be non-empty str"
            )

        if not isinstance(
            name,
            str,
        ) or name == "":
            raise ValueError(
                "name must be non-empty str"
            )

        if not isinstance(
            description,
            str,
        ):
            raise TypeError(
                "description must be str"
            )

        if not isinstance(
            sources,
            (list, tuple),
        ) or len(
            sources
        ) == 0:
            raise ValueError(
                "sources must be non-empty list/tuple"
            )

        normalized = []
        seen_paths = {}

        for source in sources:
            if not isinstance(
                source,
                DatasetSourceConfig,
            ):
                raise TypeError(
                    "sources entries must be DatasetSourceConfig"
                )

            if source.path in seen_paths:
                raise ValueError(
                    "duplicate source path in dataset: "
                    + source.path
                )

            seen_paths[
                source.path
            ] = True
            normalized.append(
                source
            )

        if metadata is None:
            metadata = {}

        if not isinstance(
            metadata,
            dict,
        ):
            raise TypeError(
                "metadata must be dict or None"
            )

        self.dataset_id = (
            dataset_id
        )
        self.name = name
        self.sources = normalized
        self.description = (
            description
        )
        self.metadata = self._copy(
            metadata
        )
        self.enabled = bool(
            enabled
        )

    def required_sources(
        self,
    ):
        return [
            source
            for source
            in self.sources
            if source.required
        ]

    def to_dict(
        self,
    ):
        return {
            "dataset_id": (
                self.dataset_id
            ),
            "name": self.name,
            "description": (
                self.description
            ),
            "enabled": self.enabled,
            "metadata": self._copy(
                self.metadata
            ),
            "sources": [
                source.to_dict()
                for source
                in self.sources
            ],
        }

    def _copy(
        self,
        value,
    ):
        if isinstance(
            value,
            dict,
        ):
            return {
                key: self._copy(
                    value[key]
                )
                for key
                in value
            }

        if isinstance(
            value,
            (list, tuple),
        ):
            return [
                self._copy(item)
                for item
                in value
            ]

        return value
