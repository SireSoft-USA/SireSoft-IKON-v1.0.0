class ModelVersion:
    """
    Registry record for one immutable model checkpoint version.
    """

    VALID_STATUSES = (
        "registered",
        "staged",
        "active",
        "deprecated",
    )

    def __init__(
        self,
        model_id,
        version,
        checkpoint_path,
        checkpoint_checksum,
        checkpoint_bytes,
        parameter_count,
        architecture=None,
        metadata=None,
        status="registered",
    ):
        if not isinstance(model_id, str) or model_id == "":
            raise ValueError("model_id must be non-empty str")

        if not isinstance(version, str) or version == "":
            raise ValueError("version must be non-empty str")

        if not isinstance(checkpoint_path, str) or checkpoint_path == "":
            raise ValueError("checkpoint_path must be non-empty str")

        if (
            not isinstance(checkpoint_checksum, str)
            or checkpoint_checksum == ""
        ):
            raise ValueError(
                "checkpoint_checksum must be non-empty str"
            )

        if (
            not isinstance(checkpoint_bytes, int)
            or checkpoint_bytes <= 0
        ):
            raise ValueError(
                "checkpoint_bytes must be positive int"
            )

        if (
            not isinstance(parameter_count, int)
            or parameter_count < 0
        ):
            raise ValueError(
                "parameter_count must be non-negative int"
            )

        if status not in self.VALID_STATUSES:
            raise ValueError("invalid model version status")

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
        self.checkpoint_path = checkpoint_path
        self.checkpoint_checksum = checkpoint_checksum
        self.checkpoint_bytes = checkpoint_bytes
        self.parameter_count = parameter_count
        self.architecture = self._copy(architecture)
        self.metadata = self._copy(metadata)
        self.status = status

    def key(self):
        return (
            self.model_id
            + "@"
            + self.version
        )

    def stage(self):
        if self.status == "deprecated":
            raise RuntimeError(
                "deprecated model version cannot be staged"
            )

        self.status = "staged"
        return self

    def activate(self):
        if self.status == "deprecated":
            raise RuntimeError(
                "deprecated model version cannot be activated"
            )

        self.status = "active"
        return self

    def deprecate(self):
        self.status = "deprecated"
        return self

    def to_dict(self):
        return {
            "model_id": self.model_id,
            "version": self.version,
            "checkpoint_path": self.checkpoint_path,
            "checkpoint_checksum": self.checkpoint_checksum,
            "checkpoint_bytes": self.checkpoint_bytes,
            "parameter_count": self.parameter_count,
            "architecture": self._copy(self.architecture),
            "metadata": self._copy(self.metadata),
            "status": self.status,
        }

    @classmethod
    def from_dict(cls, value):
        if not isinstance(value, dict):
            raise TypeError("model version state must be dict")

        return cls(
            model_id=value["model_id"],
            version=value["version"],
            checkpoint_path=value["checkpoint_path"],
            checkpoint_checksum=value["checkpoint_checksum"],
            checkpoint_bytes=int(value["checkpoint_bytes"]),
            parameter_count=int(value["parameter_count"]),
            architecture=value.get("architecture", {}),
            metadata=value.get("metadata", {}),
            status=value.get("status", "registered"),
        )

    def _copy(self, value):
        if isinstance(value, dict):
            result = {}

            for key in value:
                result[key] = self._copy(value[key])

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
