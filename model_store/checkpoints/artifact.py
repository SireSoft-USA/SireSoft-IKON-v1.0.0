class CheckpointArtifact:
    """
    Immutable model-store descriptor for one checkpoint file.

    This descriptor never contains model parameter values; it only stores
    identity, file integrity, architecture summary, and metadata.
    """

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
        for name, value in (
            ("model_id", model_id),
            ("version", version),
            ("path", path),
            ("checksum", checksum),
        ):
            if not isinstance(value, str) or value == "":
                raise ValueError(
                    name + " must be non-empty str"
                )

        if (
            not isinstance(byte_count, int)
            or byte_count <= 0
        ):
            raise ValueError(
                "byte_count must be positive int"
            )

        if (
            not isinstance(parameter_count, int)
            or parameter_count < 0
        ):
            raise ValueError(
                "parameter_count must be non-negative int"
            )

        if (
            not isinstance(parameter_tensors, int)
            or parameter_tensors < 0
        ):
            raise ValueError(
                "parameter_tensors must be non-negative int"
            )

        if architecture is None:
            architecture = {}

        if metadata is None:
            metadata = {}

        if not isinstance(architecture, dict):
            raise TypeError(
                "architecture must be dict or None"
            )

        if not isinstance(metadata, dict):
            raise TypeError(
                "metadata must be dict or None"
            )

        self.model_id = model_id
        self.version = version
        self.path = path
        self.checksum = checksum
        self.byte_count = byte_count
        self.parameter_count = parameter_count
        self.parameter_tensors = parameter_tensors
        self.architecture = self._copy(
            architecture
        )
        self.metadata = self._copy(
            metadata
        )

    def key(self):
        return (
            self.model_id
            + "@"
            + self.version
        )

    def to_dict(self):
        return {
            "model_id": self.model_id,
            "version": self.version,
            "path": self.path,
            "checksum": self.checksum,
            "byte_count": self.byte_count,
            "parameter_count": self.parameter_count,
            "parameter_tensors": self.parameter_tensors,
            "architecture": self._copy(
                self.architecture
            ),
            "metadata": self._copy(
                self.metadata
            ),
        }

    @classmethod
    def from_dict(cls, value):
        if not isinstance(value, dict):
            raise TypeError(
                "checkpoint artifact state must be dict"
            )

        return cls(
            model_id=value["model_id"],
            version=value["version"],
            path=value["path"],
            checksum=value["checksum"],
            byte_count=int(
                value["byte_count"]
            ),
            parameter_count=int(
                value.get(
                    "parameter_count",
                    0,
                )
            ),
            parameter_tensors=int(
                value.get(
                    "parameter_tensors",
                    0,
                )
            ),
            architecture=value.get(
                "architecture",
                {},
            ),
            metadata=value.get(
                "metadata",
                {},
            ),
        )

    def _copy(self, value):
        if isinstance(value, dict):
            result = {}

            for key in value:
                result[
                    key
                ] = self._copy(
                    value[key]
                )

            return result

        if isinstance(value, list):
            return [
                self._copy(item)
                for item in value
            ]

        if isinstance(value, tuple):
            return [
                self._copy(item)
                for item in value
            ]

        return value
