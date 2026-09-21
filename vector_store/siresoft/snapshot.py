class SireSoftVectorSnapshot:
    """
    Immutable descriptor for one persisted SireSoft retrieval snapshot.

    The actual vectors/documents remain inside the existing RetrievalPersistence
    snapshot. This object stores only identity, integrity, compatibility, and
    collection-level summary metadata.
    """

    COLLECTION_ID = "siresoft"

    def __init__(
        self,
        version,
        path,
        file_checksum,
        byte_count,
        created_at,
        documents,
        chunks,
        index_entries,
        dimension,
        tokenizer_signature,
        metadata=None,
    ):
        if not isinstance(version, str) or version == "":
            raise ValueError(
                "version must be non-empty str"
            )

        if not isinstance(path, str) or path == "":
            raise ValueError(
                "path must be non-empty str"
            )

        if not isinstance(file_checksum, int):
            raise TypeError(
                "file_checksum must be int"
            )

        for field_name, value in (
            ("byte_count", byte_count),
            ("documents", documents),
            ("chunks", chunks),
            ("index_entries", index_entries),
            ("dimension", dimension),
        ):
            if (
                not isinstance(value, int)
                or value < 0
            ):
                raise ValueError(
                    field_name
                    + " must be non-negative int"
                )

        if byte_count <= 0:
            raise ValueError(
                "byte_count must be positive"
            )

        if dimension <= 0:
            raise ValueError(
                "dimension must be positive"
            )

        if (
            not isinstance(created_at, int)
            or created_at < 0
        ):
            raise ValueError(
                "created_at must be non-negative int"
            )

        if (
            not isinstance(tokenizer_signature, str)
            or tokenizer_signature == ""
        ):
            raise ValueError(
                "tokenizer_signature must be non-empty str"
            )

        if metadata is None:
            metadata = {}

        if not isinstance(metadata, dict):
            raise TypeError(
                "metadata must be dict or None"
            )

        self.version = version
        self.path = path
        self.file_checksum = file_checksum
        self.byte_count = byte_count
        self.created_at = created_at
        self.documents = documents
        self.chunks = chunks
        self.index_entries = index_entries
        self.dimension = dimension
        self.tokenizer_signature = tokenizer_signature
        self.metadata = self._copy(
            metadata
        )

    def key(
        self,
    ):
        return (
            self.COLLECTION_ID
            + "@"
            + self.version
        )

    def to_dict(
        self,
    ):
        return {
            "collection_id": (
                self.COLLECTION_ID
            ),
            "version": self.version,
            "path": self.path,
            "file_checksum": (
                self.file_checksum
            ),
            "byte_count": (
                self.byte_count
            ),
            "created_at": (
                self.created_at
            ),
            "documents": (
                self.documents
            ),
            "chunks": self.chunks,
            "index_entries": (
                self.index_entries
            ),
            "dimension": (
                self.dimension
            ),
            "tokenizer_signature": (
                self.tokenizer_signature
            ),
            "metadata": self._copy(
                self.metadata
            ),
        }

    @classmethod
    def from_dict(
        cls,
        value,
    ):
        if not isinstance(
            value,
            dict,
        ):
            raise TypeError(
                "snapshot state must be dict"
            )

        if value.get(
            "collection_id"
        ) != cls.COLLECTION_ID:
            raise ValueError(
                "snapshot collection_id must be siresoft"
            )

        return cls(
            version=value[
                "version"
            ],
            path=value[
                "path"
            ],
            file_checksum=int(
                value[
                    "file_checksum"
                ]
            ),
            byte_count=int(
                value[
                    "byte_count"
                ]
            ),
            created_at=int(
                value[
                    "created_at"
                ]
            ),
            documents=int(
                value.get(
                    "documents",
                    0,
                )
            ),
            chunks=int(
                value.get(
                    "chunks",
                    0,
                )
            ),
            index_entries=int(
                value.get(
                    "index_entries",
                    0,
                )
            ),
            dimension=int(
                value[
                    "dimension"
                ]
            ),
            tokenizer_signature=value[
                "tokenizer_signature"
            ],
            metadata=value.get(
                "metadata",
                {},
            ),
        )

    def _copy(
        self,
        value,
    ):
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
