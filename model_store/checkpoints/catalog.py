class CheckpointCatalog:
    """
    Deterministic in-memory catalog for immutable checkpoint artifacts.
    """

    def __init__(self):
        self._models = {}
        self._model_order = []
        self._version_order = {}

    def add(
        self,
        artifact,
    ):
        if not isinstance(
            artifact,
            CheckpointArtifact,
        ):
            raise TypeError(
                "artifact must be CheckpointArtifact"
            )

        if self.contains(
            artifact.model_id,
            artifact.version,
        ):
            raise ValueError(
                "checkpoint artifact already exists: "
                + artifact.key()
            )

        if artifact.model_id not in self._models:
            self._models[
                artifact.model_id
            ] = {}

            self._version_order[
                artifact.model_id
            ] = []

            self._model_order.append(
                artifact.model_id
            )

        self._models[
            artifact.model_id
        ][
            artifact.version
        ] = artifact

        self._version_order[
            artifact.model_id
        ].append(
            artifact.version
        )

        return artifact

    def contains(
        self,
        model_id,
        version,
    ):
        return (
            model_id
            in self._models
            and version
            in self._models[
                model_id
            ]
        )

    def get(
        self,
        model_id,
        version,
    ):
        if not self.contains(
            model_id,
            version,
        ):
            raise KeyError(
                "checkpoint artifact not found: "
                + str(model_id)
                + "@"
                + str(version)
            )

        return self._models[
            model_id
        ][
            version
        ]

    def versions(
        self,
        model_id,
    ):
        if model_id not in self._models:
            return []

        return [
            self._models[
                model_id
            ][
                version
            ]
            for version
            in self._version_order[
                model_id
            ]
        ]

    def models(
        self,
    ):
        return [
            {
                "model_id": model_id,
                "versions": list(
                    self._version_order[
                        model_id
                    ]
                ),
                "version_count": len(
                    self._version_order[
                        model_id
                    ]
                ),
            }
            for model_id
            in self._model_order
        ]

    def export_state(
        self,
    ):
        return {
            "format": (
                "SireLLMCheckpointCatalog"
            ),
            "version": 1,
            "artifacts": [
                artifact.to_dict()
                for model_id
                in self._model_order
                for artifact
                in self.versions(
                    model_id
                )
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
                "catalog state must be dict"
            )

        if state.get(
            "format"
        ) != "SireLLMCheckpointCatalog":
            raise ValueError(
                "invalid checkpoint catalog format"
            )

        if int(
            state.get(
                "version",
                0,
            )
        ) != 1:
            raise ValueError(
                "unsupported checkpoint catalog version"
            )

        staged = CheckpointCatalog()

        for item in state.get(
            "artifacts",
            [],
        ):
            staged.add(
                CheckpointArtifact.from_dict(
                    item
                )
            )

        self._models = staged._models
        self._model_order = staged._model_order
        self._version_order = staged._version_order

        return self

    def count(
        self,
    ):
        total = 0

        for model_id in self._model_order:
            total += len(
                self._version_order[
                    model_id
                ]
            )

        return total
