class CheckpointCatalog:
    """In-memory deterministic catalog of checkpoint artifacts."""

    def __init__(self):
        self._items = {}
        self._model_order = []
        self._version_order = {}

    def add(self, artifact):
        if not isinstance(artifact, CheckpointArtifact):
            raise TypeError("artifact must be CheckpointArtifact")
        model_id = artifact.model_id
        version = artifact.version
        if self.contains(model_id, version):
            raise ValueError("checkpoint already catalogued: " + artifact.key())
        if model_id not in self._items:
            self._items[model_id] = {}
            self._version_order[model_id] = []
            self._model_order.append(model_id)
        self._items[model_id][version] = artifact
        self._version_order[model_id].append(version)
        return artifact

    def contains(self, model_id, version):
        return model_id in self._items and version in self._items[model_id]

    def get(self, model_id, version):
        if not self.contains(model_id, version):
            raise KeyError("checkpoint not found: " + str(model_id) + "@" + str(version))
        return self._items[model_id][version]

    def models(self):
        return [
            {
                "model_id": model_id,
                "versions": list(self._version_order[model_id]),
                "version_count": len(self._version_order[model_id]),
            }
            for model_id in self._model_order
        ]

    def versions(self, model_id):
        if model_id not in self._items:
            return []
        return [self._items[model_id][version] for version in self._version_order[model_id]]

    def count(self):
        total = 0
        for model_id in self._items:
            total += len(self._items[model_id])
        return total
