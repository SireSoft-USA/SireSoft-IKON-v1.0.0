class VectorIndexArtifact:
    """
    Immutable descriptor for one persisted vector-index artifact.
    """

    def __init__(
        self,
        index_id,
        version,
        path,
        file_checksum,
        byte_count,
        dimension,
        entry_count,
        created_at,
        metric_name="cosine",
        metadata=None,
    ):
        for field_name, value in (
            ("index_id", index_id),
            ("version", version),
            ("path", path),
            ("metric_name", metric_name),
        ):
            if not isinstance(value, str) or value == "":
                raise ValueError(
                    field_name + " must be non-empty str"
                )

        if not isinstance(file_checksum, int):
            raise TypeError(
                "file_checksum must be int"
            )

        for field_name, value in (
            ("byte_count", byte_count),
            ("dimension", dimension),
            ("entry_count", entry_count),
            ("created_at", created_at),
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

        if metadata is None:
            metadata = {}

        if not isinstance(metadata, dict):
            raise TypeError(
                "metadata must be dict or None"
            )

        self.index_id = index_id
        self.version = version
        self.path = path
        self.file_checksum = file_checksum
        self.byte_count = byte_count
        self.dimension = dimension
        self.entry_count = entry_count
        self.created_at = created_at
        self.metric_name = metric_name
        self.metadata = self._copy(
            metadata
        )

    def key(
        self,
    ):
        return (
            self.index_id
            + "@"
            + self.version
        )

    def to_dict(
        self,
    ):
        return {
            "index_id": self.index_id,
            "version": self.version,
            "path": self.path,
            "file_checksum": (
                self.file_checksum
            ),
            "byte_count": (
                self.byte_count
            ),
            "dimension": (
                self.dimension
            ),
            "entry_count": (
                self.entry_count
            ),
            "created_at": (
                self.created_at
            ),
            "metric_name": (
                self.metric_name
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
                "vector-index artifact state must be dict"
            )

        return cls(
            index_id=value[
                "index_id"
            ],
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
            dimension=int(
                value[
                    "dimension"
                ]
            ),
            entry_count=int(
                value[
                    "entry_count"
                ]
            ),
            created_at=int(
                value[
                    "created_at"
                ]
            ),
            metric_name=value.get(
                "metric_name",
                "cosine",
            ),
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
                    value[
                        key
                    ]
                )

            return result

        if isinstance(value, list):
            return [
                self._copy(
                    item
                )
                for item in value
            ]

        if isinstance(value, tuple):
            return [
                self._copy(
                    item
                )
                for item in value
            ]

        return value
