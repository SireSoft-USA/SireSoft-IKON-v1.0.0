class PreprocessingConfig:
    """
    Raw -> canonical execution plan.

    Raw inputs remain immutable. Canonical outputs are written separately.
    """

    def __init__(
        self,
        datasets,
        allow_default_sources=True,
        require_canonical_outputs=False,
        metadata=None,
    ):
        if not isinstance(
            datasets,
            (list, tuple),
        ) or len(datasets) == 0:
            raise ValueError(
                "datasets must be non-empty list/tuple"
            )

        normalized = []
        seen = {}

        for item in datasets:
            if not isinstance(
                item,
                DatasetPreprocessingConfig,
            ):
                raise TypeError(
                    "datasets entries must be DatasetPreprocessingConfig"
                )

            if item.dataset_id in seen:
                raise ValueError(
                    "duplicate preprocessing dataset: "
                    + item.dataset_id
                )

            seen[item.dataset_id] = True
            normalized.append(item)

        if metadata is None:
            metadata = {}

        if not isinstance(metadata, dict):
            raise TypeError(
                "metadata must be dict or None"
            )

        self.datasets = normalized
        self.allow_default_sources = bool(
            allow_default_sources
        )
        self.require_canonical_outputs = bool(
            require_canonical_outputs
        )
        self.metadata = self._copy(metadata)

    def enabled_datasets(self):
        return [
            item
            for item in self.datasets
            if item.enabled
        ]

    def dataset_map(self):
        return {
            item.dataset_id: item
            for item in self.datasets
        }

    def to_dict(self):
        return {
            "datasets": [
                item.to_dict()
                for item in self.datasets
            ],
            "allow_default_sources": (
                self.allow_default_sources
            ),
            "require_canonical_outputs": (
                self.require_canonical_outputs
            ),
            "metadata": self._copy(
                self.metadata
            ),
        }

    def _copy(self, value):
        if isinstance(value, dict):
            return {
                key: self._copy(value[key])
                for key in value
            }

        if isinstance(value, (list, tuple)):
            return [
                self._copy(item)
                for item in value
            ]

        return value
