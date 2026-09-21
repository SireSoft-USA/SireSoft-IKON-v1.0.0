class VectorIndexCatalog:
    """
    Deterministic multi-index, multi-version artifact catalog.
    """

    def __init__(
        self,
    ):
        self._indexes = {}
        self._index_order = []
        self._version_order = {}
        self._active = {}

    def add(
        self,
        artifact,
    ):
        if not isinstance(
            artifact,
            VectorIndexArtifact,
        ):
            raise TypeError(
                "artifact must be VectorIndexArtifact"
            )

        if self.contains(
            artifact.index_id,
            artifact.version,
        ):
            raise ValueError(
                "vector index artifact already exists: "
                + artifact.key()
            )

        if artifact.index_id not in self._indexes:
            self._indexes[
                artifact.index_id
            ] = {}

            self._version_order[
                artifact.index_id
            ] = []

            self._index_order.append(
                artifact.index_id
            )

            self._active[
                artifact.index_id
            ] = None

        self._indexes[
            artifact.index_id
        ][
            artifact.version
        ] = artifact

        self._version_order[
            artifact.index_id
        ].append(
            artifact.version
        )

        return artifact

    def contains(
        self,
        index_id,
        version,
    ):
        return (
            index_id
            in self._indexes
            and version
            in self._indexes[
                index_id
            ]
        )

    def get(
        self,
        index_id,
        version,
    ):
        if not self.contains(
            index_id,
            version,
        ):
            raise KeyError(
                "vector index artifact not found: "
                + str(
                    index_id
                )
                + "@"
                + str(
                    version
                )
            )

        return self._indexes[
            index_id
        ][
            version
        ]

    def activate(
        self,
        index_id,
        version,
    ):
        artifact = self.get(
            index_id,
            version,
        )

        self._active[
            index_id
        ] = version

        return artifact

    def active(
        self,
        index_id,
    ):
        if index_id not in self._indexes:
            raise KeyError(
                "vector index not found: "
                + str(
                    index_id
                )
            )

        version = self._active[
            index_id
        ]

        if version is None:
            return None

        return self._indexes[
            index_id
        ][
            version
        ]

    def versions(
        self,
        index_id,
    ):
        if index_id not in self._indexes:
            return []

        return [
            self._indexes[
                index_id
            ][
                version
            ]
            for version
            in self._version_order[
                index_id
            ]
        ]

    def indexes(
        self,
    ):
        return [
            {
                "index_id": index_id,
                "versions": list(
                    self._version_order[
                        index_id
                    ]
                ),
                "version_count": len(
                    self._version_order[
                        index_id
                    ]
                ),
                "active_version": (
                    self._active[
                        index_id
                    ]
                ),
            }
            for index_id
            in self._index_order
        ]

    def count(
        self,
    ):
        total = 0

        for index_id in self._index_order:
            total += len(
                self._version_order[
                    index_id
                ]
            )

        return total

    def export_state(
        self,
    ):
        return {
            "format": (
                "SireLLMVectorIndexCatalog"
            ),
            "version": 1,
            "indexes": [
                {
                    "index_id": index_id,
                    "active_version": (
                        self._active[
                            index_id
                        ]
                    ),
                    "artifacts": [
                        artifact.to_dict()
                        for artifact
                        in self.versions(
                            index_id
                        )
                    ],
                }
                for index_id
                in self._index_order
            ],
        }

    def load_state(
        self,
        state,
    ):
        if not isinstance(
            state,
            dict,
        ):
            raise TypeError(
                "vector-index catalog state must be dict"
            )

        if state.get(
            "format"
        ) != "SireLLMVectorIndexCatalog":
            raise ValueError(
                "invalid vector-index catalog format"
            )

        if int(
            state.get(
                "version",
                0,
            )
        ) != 1:
            raise ValueError(
                "unsupported vector-index catalog version"
            )

        staged = (
            VectorIndexCatalog()
        )

        for row in state.get(
            "indexes",
            [],
        ):
            index_id = row[
                "index_id"
            ]

            for artifact_state in row.get(
                "artifacts",
                [],
            ):
                artifact = (
                    VectorIndexArtifact
                    .from_dict(
                        artifact_state
                    )
                )

                if artifact.index_id != index_id:
                    raise ValueError(
                        "catalog index_id mismatch"
                    )

                staged.add(
                    artifact
                )

            active = row.get(
                "active_version"
            )

            if active is not None:
                staged.activate(
                    index_id,
                    active,
                )

        self._indexes = (
            staged._indexes
        )
        self._index_order = (
            staged._index_order
        )
        self._version_order = (
            staged._version_order
        )
        self._active = (
            staged._active
        )

        return self
