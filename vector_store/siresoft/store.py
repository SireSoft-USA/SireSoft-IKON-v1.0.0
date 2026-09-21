import os


class SireSoftVectorStore:
    """
    Versioned immutable store for the SireSoft retrieval corpus.

    It reuses RetrievalManager/ RetrievalPersistence instead of inventing a
    second embedding or vector-index format. Each stored artifact is therefore
    a complete retrieval snapshot: source documents, chunking config, TF-IDF
    state, exact vector index, and tokenizer compatibility signature.
    """

    def __init__(
        self,
        root_path,
        catalog=None,
        path_policy=None,
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

        self.catalog = (
            SireSoftVectorCatalog()
            if catalog is None
            else catalog
        )

        self.path_policy = (
            SireSoftVectorPathPolicy(
                self.root_path
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
        version,
        retrieval_manager,
        created_at,
        metadata=None,
        activate=False,
    ):
        self.path_policy._segment(
            version
        )

        self._validate_manager(
            retrieval_manager
        )

        if self.catalog.contains(
            version
        ):
            raise ValueError(
                "SireSoft vector snapshot version already stored: "
                + version
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

        state = (
            retrieval_manager
            .export_state()
        )

        self._validate_siresoft_state(
            state
        )

        destination = (
            self.path_policy
            .snapshot_path(
                version
            )
        )

        if os.path.exists(
            destination
        ):
            raise FileExistsError(
                "immutable SireSoft vector snapshot already exists: "
                + destination
            )

        saved = (
            retrieval_manager
            .save_state(
                destination
            )
        )

        try:
            observed_state = (
                retrieval_manager
                .persistence
                .read_state(
                    destination
                )
            )

            if observed_state != state:
                raise ValueError(
                    "stored retrieval snapshot state differs from source"
                )

            file_checksum = (
                self._file_checksum(
                    destination
                )
            )

            byte_count = (
                os.path.getsize(
                    destination
                )
            )

            status = (
                retrieval_manager
                .status()
            )

            snapshot = (
                SireSoftVectorSnapshot(
                    version=version,
                    path=destination,
                    file_checksum=(
                        file_checksum
                    ),
                    byte_count=(
                        byte_count
                    ),
                    created_at=(
                        created_at
                    ),
                    documents=status[
                        "documents"
                    ],
                    chunks=status[
                        "chunks"
                    ],
                    index_entries=status[
                        "index_entries"
                    ],
                    dimension=status[
                        "dimension"
                    ],
                    tokenizer_signature=status[
                        "tokenizer_signature"
                    ],
                    metadata=metadata,
                )
            )

            self.catalog.add(
                snapshot
            )

            if activate:
                self.catalog.activate(
                    version
                )

            return snapshot

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
        version,
        retrieval_manager=None,
    ):
        snapshot = self.catalog.get(
            version
        )

        if not os.path.exists(
            snapshot.path
        ):
            return {
                "valid": False,
                "version": version,
                "file_exists": False,
                "file_checksum_match": False,
                "retrieval_snapshot_valid": False,
                "tokenizer_compatible": None,
                "error": (
                    "snapshot file missing"
                ),
            }

        observed_checksum = (
            self._file_checksum(
                snapshot.path
            )
        )

        checksum_match = (
            observed_checksum
            == snapshot.file_checksum
        )

        state_valid = False
        state = None
        error = None

        if retrieval_manager is not None:
            self._validate_manager(
                retrieval_manager
            )

            try:
                state = (
                    retrieval_manager
                    .persistence
                    .read_state(
                        snapshot.path
                    )
                )

                state_valid = True

            except Exception as exc:
                error = str(
                    exc
                )

        else:
            state_valid = (
                checksum_match
            )

        tokenizer_compatible = None
        summary_match = None

        if (
            retrieval_manager
            is not None
            and state_valid
        ):
            tokenizer_compatible = (
                state[
                    "tokenizer_signature"
                ]
                == retrieval_manager
                .tokenizer_signature()
            )

            summary_match = (
                int(
                    state[
                        "embedder"
                    ][
                        "dimension"
                    ]
                )
                == snapshot.dimension
                and len(
                    state[
                        "documents"
                    ]
                )
                == snapshot.documents
                and len(
                    state[
                        "index"
                    ][
                        "entries"
                    ]
                )
                == snapshot.index_entries
                and state[
                    "tokenizer_signature"
                ]
                == snapshot.tokenizer_signature
            )

        valid = (
            checksum_match
            and state_valid
            and (
                tokenizer_compatible
                is None
                or tokenizer_compatible
            )
            and (
                summary_match
                is None
                or summary_match
            )
        )

        return {
            "valid": valid,
            "version": version,
            "file_exists": True,
            "file_checksum_match": (
                checksum_match
            ),
            "retrieval_snapshot_valid": (
                state_valid
            ),
            "tokenizer_compatible": (
                tokenizer_compatible
            ),
            "summary_match": (
                summary_match
            ),
            "stored_checksum": (
                snapshot.file_checksum
            ),
            "observed_checksum": (
                observed_checksum
            ),
            "error": error,
        }

    def load_into(
        self,
        retrieval_manager,
        version=None,
    ):
        self._validate_manager(
            retrieval_manager
        )

        if version is None:
            active = (
                self.catalog
                .active()
            )

            if active is None:
                raise RuntimeError(
                    "no active SireSoft vector snapshot"
                )

            snapshot = active

        else:
            snapshot = (
                self.catalog
                .get(
                    version
                )
            )

        verification = self.verify(
            snapshot.version,
            retrieval_manager=(
                retrieval_manager
            ),
        )

        if not verification[
            "valid"
        ]:
            raise ValueError(
                "SireSoft vector snapshot verification failed"
            )

        retrieval_manager.load_state_file(
            snapshot.path
        )

        return {
            "snapshot": (
                snapshot.to_dict()
            ),
            "retrieval_status": (
                retrieval_manager
                .status()
            ),
        }

    def activate(
        self,
        version,
    ):
        return self.catalog.activate(
            version
        )

    def active(
        self,
    ):
        snapshot = (
            self.catalog.active()
        )

        if snapshot is None:
            return None

        return snapshot.to_dict()

    def get(
        self,
        version,
    ):
        return self.catalog.get(
            version
        )

    def list_snapshots(
        self,
    ):
        return (
            self.catalog
            .list_snapshots()
        )

    def status(
        self,
    ):
        return {
            "ready": True,
            "collection_id": (
                SireSoftVectorSnapshot
                .COLLECTION_ID
            ),
            "root_path": (
                self.root_path
            ),
            "snapshot_count": (
                self.catalog.count()
            ),
            "active_version": (
                self.catalog
                .active_version()
            ),
            "immutable": True,
            "retrieval_format": (
                "SireLLMRetrievalState"
            ),
        }

    def _validate_manager(
        self,
        retrieval_manager,
    ):
        for name in (
            "export_state",
            "save_state",
            "load_state_file",
            "status",
            "tokenizer_signature",
        ):
            if not hasattr(
                retrieval_manager,
                name,
            ):
                raise TypeError(
                    "retrieval_manager must provide "
                    + name
                    + "()"
                )

        if not hasattr(
            retrieval_manager,
            "persistence",
        ) or not hasattr(
            retrieval_manager.persistence,
            "read_state",
        ):
            raise TypeError(
                "retrieval_manager.persistence must provide read_state()"
            )

    def _validate_siresoft_state(
        self,
        state,
    ):
        if not isinstance(
            state,
            dict,
        ):
            raise TypeError(
                "retrieval state must be dict"
            )

        if state.get(
            "format"
        ) != "SireLLMRetrievalState":
            raise ValueError(
                "expected SireLLM retrieval state"
            )

        documents = state.get(
            "documents",
            [],
        )

        if len(
            documents
        ) == 0:
            raise ValueError(
                "SireSoft vector store requires at least one document"
            )

        for document in documents:
            if document.get(
                "dataset_id"
            ) != "siresoft":
                raise ValueError(
                    "SireSoft vector store only accepts dataset_id='siresoft'"
                )

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
