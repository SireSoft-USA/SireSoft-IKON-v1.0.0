import os


class VectorIndexStore:
    """
    Immutable filesystem store for FlatVectorIndex artifacts.

    Persistence delegates to the existing handwritten IndexPersistence format.
    """

    def __init__(
        self,
        root_path,
        persistence=None,
        catalog=None,
        path_policy=None,
        bridge=None,
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
            IndexPersistence()
            if persistence is None
            else persistence
        )

        self.catalog = (
            VectorIndexCatalog()
            if catalog is None
            else catalog
        )

        self.path_policy = (
            VectorIndexPathPolicy(
                self.root_path
            )
            if path_policy is None
            else path_policy
        )

        self.bridge = (
            RetrievalIndexBridge()
            if bridge is None
            else bridge
        )

        os.makedirs(
            self.root_path,
            exist_ok=True,
        )

    def put_index(
        self,
        index_id,
        version,
        index,
        created_at,
        metadata=None,
        metric_name="cosine",
        activate=False,
    ):
        self.path_policy._segment(
            index_id,
            "index_id",
        )

        self.path_policy._segment(
            version,
            "version",
        )

        if not isinstance(
            index,
            FlatVectorIndex,
        ):
            raise TypeError(
                "index must be FlatVectorIndex"
            )

        if (
            not isinstance(
                created_at,
                int,
            )
            or created_at < 0
        ):
            raise ValueError(
                "created_at must be non-negative int"
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

        if not isinstance(
            metric_name,
            str,
        ) or metric_name == "":
            raise ValueError(
                "metric_name must be non-empty str"
            )

        if self.catalog.contains(
            index_id,
            version,
        ):
            raise ValueError(
                "vector index version already catalogued: "
                + index_id
                + "@"
                + version
            )

        destination = (
            self.path_policy
            .artifact_path(
                index_id,
                version,
            )
        )

        if os.path.exists(
            destination
        ):
            raise FileExistsError(
                "immutable vector-index destination already exists: "
                + destination
            )

        os.makedirs(
            self.path_policy
            .index_directory(
                index_id
            ),
            exist_ok=True,
        )

        state = index.state_dict()

        saved = self.persistence.save(
            destination,
            index,
        )

        try:
            observed_state = (
                self.persistence
                .read_state(
                    destination
                )
            )

            if observed_state != state:
                raise ValueError(
                    "stored vector-index state differs from source"
                )

            artifact = (
                VectorIndexArtifact(
                    index_id=index_id,
                    version=version,
                    path=destination,
                    file_checksum=(
                        self._file_checksum(
                            destination
                        )
                    ),
                    byte_count=(
                        os.path.getsize(
                            destination
                        )
                    ),
                    dimension=(
                        index.dimension
                    ),
                    entry_count=(
                        index.count()
                    ),
                    created_at=(
                        created_at
                    ),
                    metric_name=(
                        metric_name
                    ),
                    metadata=metadata,
                )
            )

            self.catalog.add(
                artifact
            )

            if activate:
                self.catalog.activate(
                    index_id,
                    version,
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

    def put_from_retrieval_manager(
        self,
        index_id,
        version,
        retrieval_manager,
        created_at,
        metadata=None,
        activate=False,
    ):
        extracted = self.bridge.extract(
            retrieval_manager
        )

        combined = self._copy(
            extracted[
                "metadata"
            ]
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
                combined[
                    key
                ] = self._copy(
                    metadata[
                        key
                    ]
                )

        return self.put_index(
            index_id=index_id,
            version=version,
            index=extracted[
                "index"
            ],
            created_at=created_at,
            metadata=combined,
            metric_name="cosine",
            activate=activate,
        )

    def verify(
        self,
        index_id,
        version,
    ):
        artifact = self.catalog.get(
            index_id,
            version,
        )

        if not os.path.exists(
            artifact.path
        ):
            return {
                "valid": False,
                "file_exists": False,
                "checksum_match": False,
                "state_valid": False,
                "dimension_match": False,
                "entry_count_match": False,
                "error": (
                    "vector-index file missing"
                ),
            }

        observed_checksum = (
            self._file_checksum(
                artifact.path
            )
        )

        checksum_match = (
            observed_checksum
            == artifact.file_checksum
        )

        try:
            state = (
                self.persistence
                .read_state(
                    artifact.path
                )
            )

            state_valid = True
            error = None

        except Exception as exc:
            state = None
            state_valid = False
            error = str(
                exc
            )

        dimension_match = False
        entry_count_match = False

        if state_valid:
            dimension_match = (
                int(
                    state[
                        "dimension"
                    ]
                )
                == artifact.dimension
            )

            entry_count_match = (
                len(
                    state[
                        "entries"
                    ]
                )
                == artifact.entry_count
            )

        return {
            "valid": (
                checksum_match
                and state_valid
                and dimension_match
                and entry_count_match
            ),
            "file_exists": True,
            "checksum_match": (
                checksum_match
            ),
            "state_valid": (
                state_valid
            ),
            "dimension_match": (
                dimension_match
            ),
            "entry_count_match": (
                entry_count_match
            ),
            "stored_checksum": (
                artifact.file_checksum
            ),
            "observed_checksum": (
                observed_checksum
            ),
            "error": error,
        }

    def load_index(
        self,
        index_id,
        version=None,
        metric=None,
    ):
        if version is None:
            artifact = (
                self.catalog
                .active(
                    index_id
                )
            )

            if artifact is None:
                raise RuntimeError(
                    "vector index has no active version"
                )

        else:
            artifact = (
                self.catalog
                .get(
                    index_id,
                    version,
                )
            )

        verification = self.verify(
            artifact.index_id,
            artifact.version,
        )

        if not verification[
            "valid"
        ]:
            raise ValueError(
                "vector-index artifact verification failed"
            )

        index = self.persistence.load(
            artifact.path,
            metric=metric,
        )

        return {
            "artifact": (
                artifact.to_dict()
            ),
            "index": index,
        }

    def activate(
        self,
        index_id,
        version,
    ):
        return self.catalog.activate(
            index_id,
            version,
        )

    def active(
        self,
        index_id,
    ):
        artifact = (
            self.catalog.active(
                index_id
            )
        )

        if artifact is None:
            return None

        return artifact.to_dict()

    def get(
        self,
        index_id,
        version,
    ):
        return self.catalog.get(
            index_id,
            version,
        )

    def list_indexes(
        self,
    ):
        return self.catalog.indexes()

    def list_versions(
        self,
        index_id,
    ):
        return [
            artifact.to_dict()
            for artifact
            in self.catalog.versions(
                index_id
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
            "index_count": len(
                self.catalog.indexes()
            ),
            "artifact_count": (
                self.catalog.count()
            ),
            "immutable": True,
            "format": (
                "SLLMVIDX"
            ),
        }

    def _file_checksum(
        self,
        path,
    ):
        handle = open(
            path,
            "rb",
        )

        try:
            data = handle.read()
        finally:
            handle.close()

        return fnv1a64(
            data
        )

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
