class DatasetCatalog:
    """
    Manifest registry for dataset discovery and service queries.
    """

    def __init__(self, manifests=None):
        self._manifests = {}
        self._order = []

        if manifests is not None:
            for manifest in manifests:
                self.register(
                    manifest
                )

    def register(self, manifest):
        if not isinstance(manifest, DatasetManifest):
            raise TypeError(
                "manifest must be DatasetManifest"
            )

        if manifest.dataset_id in self._manifests:
            raise ValueError(
                "dataset already registered: "
                + manifest.dataset_id
            )

        self._manifests[
            manifest.dataset_id
        ] = manifest

        self._order.append(
            manifest.dataset_id
        )

        return self

    def get(self, dataset_id):
        if not isinstance(dataset_id, str):
            raise TypeError(
                "dataset_id must be str"
            )

        if dataset_id not in self._manifests:
            raise KeyError(
                "dataset not registered: "
                + dataset_id
            )

        return self._manifests[
            dataset_id
        ]

    def contains(self, dataset_id):
        return dataset_id in self._manifests

    def manifests(self):
        return [
            self._manifests[
                dataset_id
            ]
            for dataset_id in self._order
        ]

    def dataset_ids(self):
        return list(
            self._order
        )

    def count(self):
        return len(
            self._order
        )

    def summaries(self):
        result = []

        for manifest in self.manifests():
            result.append({
                "dataset_id": manifest.dataset_id,
                "name": manifest.name,
                "source_count": len(
                    manifest.sources
                ),
                "required_source_count": len(
                    manifest.required_sources()
                ),
                "metadata": dict(
                    manifest.metadata
                ),
            })

        return result


def build_default_catalog():
    return DatasetCatalog(
        default_dataset_manifests()
    )
