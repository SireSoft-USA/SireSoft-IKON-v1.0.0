import os


class ManifestStore:
    """
    Immutable filesystem store for model manifests.
    """

    def __init__(
        self,
        root_path,
        persistence=None,
        validator=None,
        catalog=None,
    ):
        if not isinstance(
            root_path,
            str,
        ) or root_path == "":
            raise ValueError(
                "root_path must be non-empty str"
            )

        self.root_path = (
            root_path.rstrip(
                "/\\"
            )
        )

        self.persistence = (
            ManifestPersistence()
            if persistence is None
            else persistence
        )

        self.validator = (
            ManifestValidator()
            if validator is None
            else validator
        )

        self.catalog = (
            ManifestCatalog()
            if catalog is None
            else catalog
        )

        os.makedirs(
            self.root_path,
            exist_ok=True,
        )

    def create_from_checkpoint_store(
        self,
        checkpoint_store,
        model_id,
        version,
        created_at,
        tokenizer=None,
        runtime=None,
        metadata=None,
    ):
        if checkpoint_store is None or not hasattr(
            checkpoint_store,
            "get",
        ):
            raise TypeError(
                "checkpoint_store must provide get()"
            )

        # Validate path-facing identifiers before touching the checkpoint
        # catalog so unsafe traversal input is rejected deterministically.
        self._segment(
            model_id,
            "model_id",
        )

        self._segment(
            version,
            "version",
        )

        artifact = checkpoint_store.get(
            model_id,
            version,
        )

        manifest = ModelManifest(
            model_id=model_id,
            version=version,
            created_at=created_at,
            checkpoint={
                "path": (
                    artifact.path
                ),
                "checksum": (
                    artifact.checksum
                ),
                "byte_count": (
                    artifact.byte_count
                ),
                "parameter_count": (
                    artifact.parameter_count
                ),
                "parameter_tensors": (
                    artifact.parameter_tensors
                ),
            },
            architecture=(
                artifact.architecture
            ),
            tokenizer=tokenizer,
            runtime=runtime,
            metadata=metadata,
        )

        self.validator.validate(
            manifest
        )

        comparison = (
            self.validator
            .compare_checkpoint_artifact(
                manifest,
                artifact,
            )
        )

        if not comparison[
            "valid"
        ]:
            raise ValueError(
                "manifest checkpoint reference mismatch"
            )

        path = self._manifest_path(
            model_id,
            version,
        )

        if os.path.exists(
            path
        ):
            raise FileExistsError(
                "immutable manifest destination already exists: "
                + path
            )

        os.makedirs(
            self._model_directory(
                model_id
            ),
            exist_ok=True,
        )

        saved = self.persistence.save(
            path,
            manifest,
        )

        try:
            loaded = self.persistence.load(
                path
            )

            if loaded.to_dict() != manifest.to_dict():
                raise ValueError(
                    "stored manifest round-trip mismatch"
                )

            self.catalog.add(
                manifest=manifest,
                manifest_path=path,
                manifest_checksum=(
                    saved[
                        "checksum"
                    ]
                ),
            )

        except Exception:
            if os.path.exists(
                path
            ):
                os.remove(
                    path
                )

            raise

        return {
            "manifest": (
                manifest.to_dict()
            ),
            "path": path,
            "checksum": (
                saved[
                    "checksum"
                ]
            ),
            "bytes": (
                saved[
                    "bytes"
                ]
            ),
        }

    def load_existing(
        self,
        path,
    ):
        manifest = (
            self.persistence
            .load(
                path
            )
        )

        self.validator.validate(
            manifest
        )

        checksum = (
            self.persistence
            .file_checksum(
                path
            )
        )

        self.catalog.add(
            manifest=manifest,
            manifest_path=path,
            manifest_checksum=(
                checksum
            ),
        )

        return manifest

    def verify(
        self,
        model_id,
        version,
        checkpoint_store=None,
    ):
        entry = self.catalog.get(
            model_id,
            version,
        )

        path = entry[
            "path"
        ]

        if not os.path.exists(
            path
        ):
            return {
                "valid": False,
                "manifest_valid": False,
                "manifest_checksum_match": False,
                "checkpoint_match": None,
                "error": (
                    "manifest file missing"
                ),
            }

        try:
            loaded = (
                self.persistence
                .load(
                    path
                )
            )
        except Exception as error:
            return {
                "valid": False,
                "manifest_valid": False,
                "manifest_checksum_match": False,
                "checkpoint_match": None,
                "error": str(
                    error
                ),
            }

        observed_checksum = (
            self.persistence
            .file_checksum(
                path
            )
        )

        checksum_match = (
            observed_checksum
            == entry[
                "checksum"
            ]
        )

        content_match = (
            loaded.to_dict()
            == entry[
                "manifest"
            ].to_dict()
        )

        checkpoint_match = None

        if checkpoint_store is not None:
            artifact = (
                checkpoint_store
                .get(
                    model_id,
                    version,
                )
            )

            checkpoint_match = (
                self.validator
                .compare_checkpoint_artifact(
                    loaded,
                    artifact,
                )
            )

        valid = (
            checksum_match
            and content_match
            and (
                checkpoint_match
                is None
                or checkpoint_match[
                    "valid"
                ]
            )
        )

        return {
            "valid": valid,
            "manifest_valid": True,
            "manifest_checksum_match": (
                checksum_match
            ),
            "manifest_content_match": (
                content_match
            ),
            "checkpoint_match": (
                checkpoint_match
            ),
            "stored_checksum": (
                entry[
                    "checksum"
                ]
            ),
            "observed_checksum": (
                observed_checksum
            ),
            "error": None,
        }

    def register_with_model_registry(
        self,
        model_registry,
        model_id,
        version,
        stage=False,
        metadata=None,
    ):
        if model_registry is None or not hasattr(
            model_registry,
            "register_checkpoint",
        ):
            raise TypeError(
                "model_registry must provide register_checkpoint()"
            )

        entry = self.catalog.get(
            model_id,
            version,
        )

        manifest = entry[
            "manifest"
        ]

        combined_metadata = {
            "manifest_path": (
                entry[
                    "path"
                ]
            ),
            "manifest_checksum": (
                entry[
                    "checksum"
                ]
            ),
        }

        for key in manifest.metadata:
            combined_metadata[
                key
            ] = manifest.metadata[
                key
            ]

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
                ] = metadata[
                    key
                ]

        return model_registry.register_checkpoint(
            model_id=model_id,
            version=version,
            checkpoint_path=(
                manifest.checkpoint[
                    "path"
                ]
            ),
            metadata=(
                combined_metadata
            ),
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
        return self.catalog.versions(
            model_id
        )

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
            "manifest_count": (
                self.catalog.count()
            ),
            "immutable": True,
            "format": (
                ModelManifest.FORMAT
            ),
            "schema_version": (
                ModelManifest
                .SCHEMA_VERSION
            ),
        }

    def _manifest_path(
        self,
        model_id,
        version,
    ):
        return (
            self._model_directory(
                model_id
            )
            + "/"
            + self._segment(
                version,
                "version",
            )
            + ".sllmmanifest"
        )

    def _model_directory(
        self,
        model_id,
    ):
        return (
            self.root_path
            + "/"
            + self._segment(
                model_id,
                "model_id",
            )
        )

    def _segment(
        self,
        value,
        field_name,
    ):
        if not isinstance(
            value,
            str,
        ) or value == "":
            raise ValueError(
                field_name
                + " must be non-empty str"
            )

        if (
            "/"
            in value
            or "\\"
            in value
            or "\x00"
            in value
            or ".."
            in value
        ):
            raise ValueError(
                field_name
                + " contains unsafe path characters"
            )

        return value
