class CheckpointArtifact:
    """Immutable metadata describing one stored SireSoft-IKON checkpoint."""

    def __init__(
        self,
        model_id,
        version,
        path,
        checksum,
        byte_count,
        parameter_count,
        parameter_tensors,
        architecture=None,
        metadata=None,
    ):
        for field_name, value in (("model_id", model_id), ("version", version), ("path", path), ("checksum", checksum)):
            if not isinstance(value, str) or value == "":
                raise ValueError(field_name + " must be non-empty str")

        for field_name, value in (
            ("byte_count", byte_count),
            ("parameter_count", parameter_count),
            ("parameter_tensors", parameter_tensors),
        ):
            if not isinstance(value, int) or value < 0:
                raise ValueError(field_name + " must be non-negative int")

        if architecture is None:
            architecture = {}
        if metadata is None:
            metadata = {}
        if not isinstance(architecture, dict):
            raise TypeError("architecture must be dict or None")
        if not isinstance(metadata, dict):
            raise TypeError("metadata must be dict or None")

        self.model_id = model_id
        self.version = version
        self.path = path
        self.checksum = checksum
        self.byte_count = byte_count
        self.parameter_count = parameter_count
        self.parameter_tensors = parameter_tensors
        self.architecture = self._copy(architecture)
        self.metadata = self._copy(metadata)

    def key(self):
        return self.model_id + "@" + self.version

    def to_dict(self):
        return {
            "model_id": self.model_id,
            "version": self.version,
            "path": self.path,
            "checksum": self.checksum,
            "byte_count": self.byte_count,
            "parameter_count": self.parameter_count,
            "parameter_tensors": self.parameter_tensors,
            "architecture": self._copy(self.architecture),
            "metadata": self._copy(self.metadata),
        }

    def _copy(self, value):
        if isinstance(value, dict):
            return {key: self._copy(value[key]) for key in value}
        if isinstance(value, list):
            return [self._copy(item) for item in value]
        if isinstance(value, tuple):
            return [self._copy(item) for item in value]
        return value
