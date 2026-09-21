class DatasetsConfig:
    """
    Dataset catalog configuration.

    Raw files are declarations only. This layer never preprocesses, rewrites,
    merges, normalizes, or mutates raw dataset content.
    """

    def __init__(
        self,
        datasets,
        enforce_global_source_uniqueness=True,
        capture_immutable_baselines=False,
        metadata=None,
    ):
        if not isinstance(
            datasets,
            (list, tuple),
        ) or len(
            datasets
        ) == 0:
            raise ValueError(
                "datasets must be non-empty list/tuple"
            )

        normalized = []
        seen_ids = {}

        for dataset in datasets:
            if not isinstance(
                dataset,
                DatasetDefinitionConfig,
            ):
                raise TypeError(
                    "datasets entries must be DatasetDefinitionConfig"
                )

            if dataset.dataset_id in seen_ids:
                raise ValueError(
                    "duplicate dataset_id: "
                    + dataset.dataset_id
                )

            seen_ids[
                dataset.dataset_id
            ] = True
            normalized.append(
                dataset
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

        self.datasets = normalized
        self.enforce_global_source_uniqueness = bool(
            enforce_global_source_uniqueness
        )
        self.capture_immutable_baselines = bool(
            capture_immutable_baselines
        )
        self.metadata = self._copy(
            metadata
        )

    def enabled_datasets(
        self,
    ):
        return [
            dataset
            for dataset
            in self.datasets
            if dataset.enabled
        ]

    def dataset_map(
        self,
    ):
        return {
            dataset.dataset_id: dataset
            for dataset
            in self.datasets
        }

    def to_dict(
        self,
    ):
        return {
            "datasets": [
                dataset.to_dict()
                for dataset
                in self.datasets
            ],
            "enforce_global_source_uniqueness": (
                self.enforce_global_source_uniqueness
            ),
            "capture_immutable_baselines": (
                self.capture_immutable_baselines
            ),
            "metadata": self._copy(
                self.metadata
            ),
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
