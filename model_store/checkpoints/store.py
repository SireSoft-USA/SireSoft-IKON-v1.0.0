import os


class CheckpointStore:
    """
    Filesystem-backed immutable checkpoint store.

    Filesystem operations use only Python's standard-library os module.
    Checkpoint validation itself uses the existing handwritten CheckpointCodec
    through ModelRegistry's CheckpointInspector.
    """

    def __init__(
        self,
        root_path,
        inspector=None,
        catalog=None,
        path_policy=None,
    ):
        if not isinstance(root_path, str) or root_path == "":
            raise ValueError(
                "root_path must be non-empty str"
            )

        self.root_path = root_path

        self.inspector = (
            CheckpointInspector()
            if inspector is None
            else inspector
        )

        self.catalog = (
            CheckpointCatalog()
            if catalog is None
            else catalog
        )

        self.path_policy = (
            CheckpointPathPolicy(
                root_path
            )
            if path_policy is None
            else path_policy
        )

        os.makedirs(
            self.root_path,
            exist_ok=True,
        )

    def put(
        self,
        model_id,
        version,
        source_path,
        metadata=None,
    ):
        if self.catalog.contains(
            model_id,
            version,
        ):
            raise ValueError(
                "checkpoint version already stored: "
                + model_id
                + "@"
                + version
            )

        descriptor = self.inspector.inspect(
            source_path
        )

        destination = (
            self.path_policy
            .artifact_path(
                model_id,
                version,
            )
        )

        model_directory = (
            self.path_policy
            .model_directory(
                model_id
            )
        )

        os.makedirs(
            model_directory,
            exist_ok=True,
        )

        if os.path.exists(
            destination
        ):
            raise FileExistsError(
                "immutable checkpoint destination already exists: "
                + destination
            )

        self._copy_file(
            source_path,
            destination,
        )

        try:
            stored = self.inspector.inspect(
                destination
            )

            if (
                stored[
                    "checksum"
                ]
                != descriptor[
                    "checksum"
                ]
            ):
                raise ValueError(
                    "stored checkpoint checksum differs from source"
                )

            if (
                stored[
                    "bytes"
                ]
                != descriptor[
                    "bytes"
                ]
            ):
                raise ValueError(
                    "stored checkpoint size differs from source"
                )

            combined_metadata = (
                self._copy(
                    descriptor.get(
                        "metadata",
                        {},
                    )
                )
            )

            if metadata is not None:
                if not isinstance(
                    metadata,
                    dict,
                ):
                    raise TypeError(
                        "metadata must be dict or None"
                    )

                for key in metadata:
                    combined_metadata[
                        key
                    ] = self._copy(
                        metadata[
                            key
                        ]
                    )

            artifact = CheckpointArtifact(
                model_id=model_id,
                version=version,
                path=destination,
                checksum=stored[
                    "checksum"
                ],
                byte_count=stored[
                    "bytes"
                ],
                parameter_count=stored[
                    "parameter_count"
                ],
                parameter_tensors=stored[
                    "parameter_tensors"
                ],
                architecture=stored[
                    "architecture"
                ],
                metadata=(
                    combined_metadata
                ),
            )

            self.catalog.add(
                artifact
            )

            return artifact

        except Exception:
            if os.path.exists(
                destination
            ):
                os.remove(
                    destination
                )

            raise

    def verify(
        self,
        model_id,
        version,
    ):
        artifact = self.catalog.get(
            model_id,
            version,
        )

        observed = (
            self.inspector
            .try_inspect(
                artifact.path
            )
        )

        if not observed.get(
            "valid",
            False,
        ):
            return {
                "model_id": model_id,
                "version": version,
                "valid": False,
                "checkpoint_valid": False,
                "checksum_match": False,
                "bytes_match": False,
                "stored_checksum": (
                    artifact.checksum
                ),
                "observed_checksum": None,
                "stored_bytes": (
                    artifact.byte_count
                ),
                "observed_bytes": None,
                "error": observed.get(
                    "error"
                ),
            }

        checksum_match = (
            observed[
                "checksum"
            ]
            == artifact.checksum
        )

        bytes_match = (
            observed[
                "bytes"
            ]
            == artifact.byte_count
        )

        return {
            "model_id": model_id,
            "version": version,
            "valid": (
                checksum_match
                and bytes_match
            ),
            "checkpoint_valid": True,
            "checksum_match": (
                checksum_match
            ),
            "bytes_match": (
                bytes_match
            ),
            "stored_checksum": (
                artifact.checksum
            ),
            "observed_checksum": (
                observed[
                    "checksum"
                ]
            ),
            "stored_bytes": (
                artifact.byte_count
            ),
            "observed_bytes": (
                observed[
                    "bytes"
                ]
            ),
            "parameter_count": (
                observed[
                    "parameter_count"
                ]
            ),
        }

    def register_with_model_registry(
        self,
        model_registry,
        model_id,
        version,
        metadata=None,
        stage=False,
    ):
        if model_registry is None or not hasattr(
            model_registry,
            "register_checkpoint",
        ):
            raise TypeError(
                "model_registry must provide register_checkpoint()"
            )

        artifact = self.catalog.get(
            model_id,
            version,
        )

        return model_registry.register_checkpoint(
            model_id=model_id,
            version=version,
            checkpoint_path=(
                artifact.path
            ),
            metadata=metadata,
            stage=stage,
        )

    def get(
        self,
        model_id,
        version,
    ):
        return self.catalog.get(
            model_id,
            version,
        )

    def list_models(
        self,
    ):
        return self.catalog.models()

    def list_versions(
        self,
        model_id,
    ):
        return [
            artifact.to_dict()
            for artifact
            in self.catalog.versions(
                model_id
            )
        ]

    def status(
        self,
    ):
        return {
            "ready": True,
            "root_path": (
                self.root_path
            ),
            "model_count": len(
                self.catalog.models()
            ),
            "artifact_count": (
                self.catalog.count()
            ),
            "immutable": True,
            "checkpoint_format": (
                "SireLLMCheckpoint"
            ),
        }

    def _copy_file(
        self,
        source_path,
        destination_path,
        chunk_size=1024 * 1024,
    ):
        source = open(
            source_path,
            "rb",
        )

        try:
            destination = open(
                destination_path,
                "xb",
            )

            try:
                while True:
                    chunk = source.read(
                        chunk_size
                    )

                    if not chunk:
                        break

                    destination.write(
                        chunk
                    )

            finally:
                destination.close()

        finally:
            source.close()

    def _copy(
        self,
        value,
    ):
        if isinstance(
            value,
            dict,
        ):
            result = {}

            for key in value:
                result[
                    key
                ] = self._copy(
                    value[
                        key
                    ]
                )

            return result

        if isinstance(
            value,
            list,
        ):
            return [
                self._copy(
                    item
                )
                for item in value
            ]

        if isinstance(
            value,
            tuple,
        ):
            return [
                self._copy(
                    item
                )
                for item in value
            ]

        return value
