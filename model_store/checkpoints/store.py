import os


class CheckpointStore:
    """Immutable filesystem store backed by the current CheckpointCodec/Inspector."""

    def __init__(self, root_path, inspector=None, path_policy=None, catalog=None):
        if not isinstance(root_path, str) or root_path == "":
            raise ValueError("root_path must be non-empty str")
        self.root_path = root_path.rstrip("/\\")
        self.inspector = CheckpointInspector() if inspector is None else inspector
        self.path_policy = CheckpointPathPolicy(self.root_path) if path_policy is None else path_policy
        self.catalog = CheckpointCatalog() if catalog is None else catalog
        os.makedirs(self.root_path, exist_ok=True)

    def put(self, model_id, version, source_path, metadata=None):
        self.path_policy.segment(model_id, "model_id")
        self.path_policy.segment(version, "version")
        if not isinstance(source_path, str) or source_path == "":
            raise ValueError("source_path must be non-empty str")
        if metadata is None:
            metadata = {}
        if not isinstance(metadata, dict):
            raise TypeError("metadata must be dict or None")

        descriptor = self.inspector.inspect(source_path)
        destination = self.path_policy.checkpoint_path(model_id, version)
        if os.path.exists(destination):
            raise FileExistsError("immutable checkpoint destination already exists: " + destination)

        os.makedirs(self.path_policy.model_directory(model_id), exist_ok=True)
        temporary = destination + ".tmp"
        if os.path.exists(temporary):
            os.remove(temporary)

        source = open(source_path, "rb")
        target = open(temporary, "wb")
        try:
            while True:
                chunk = source.read(1024 * 1024)
                if not chunk:
                    break
                target.write(chunk)
        finally:
            source.close()
            target.close()

        try:
            copied = self.inspector.inspect(temporary)
            if copied["checksum"] != descriptor["checksum"] or copied["bytes"] != descriptor["bytes"]:
                raise ValueError("checkpoint copy verification failed")
            os.replace(temporary, destination)
        except Exception:
            if os.path.exists(temporary):
                os.remove(temporary)
            raise

        combined_metadata = self._copy(descriptor.get("metadata", {}))
        for key in metadata:
            combined_metadata[key] = self._copy(metadata[key])

        artifact = CheckpointArtifact(
            model_id=model_id,
            version=version,
            path=destination,
            checksum=descriptor["checksum"],
            byte_count=descriptor["bytes"],
            parameter_count=descriptor["parameter_count"],
            parameter_tensors=descriptor["parameter_tensors"],
            architecture=descriptor.get("architecture", {}),
            metadata=combined_metadata,
        )
        self.catalog.add(artifact)
        return artifact

    def get(self, model_id, version):
        return self.catalog.get(model_id, version)

    def verify(self, model_id, version):
        artifact = self.get(model_id, version)
        try:
            descriptor = self.inspector.inspect(artifact.path)
        except Exception as error:
            return {"valid": False, "error": str(error)}
        valid = (
            descriptor["checksum"] == artifact.checksum
            and descriptor["bytes"] == artifact.byte_count
            and descriptor["parameter_count"] == artifact.parameter_count
            and descriptor["parameter_tensors"] == artifact.parameter_tensors
        )
        return {"valid": valid, "descriptor": descriptor, "error": None if valid else "checkpoint metadata mismatch"}

    def status(self):
        return {
            "root_path": self.root_path,
            "model_count": len(self.catalog.models()),
            "checkpoint_count": self.catalog.count(),
            "immutable": True,
        }

    def _copy(self, value):
        if isinstance(value, dict):
            return {key: self._copy(value[key]) for key in value}
        if isinstance(value, list):
            return [self._copy(item) for item in value]
        if isinstance(value, tuple):
            return [self._copy(item) for item in value]
        return value
