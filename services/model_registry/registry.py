class ModelRegistry:
    """
    Versioned SireLLM checkpoint registry.

    Registration never mutates checkpoint files. Promotion only changes registry
    deployment state. At most one active version exists per model_id.
    """

    def __init__(
        self,
        inspector=None,
    ):
        self.inspector = (
            CheckpointInspector()
            if inspector is None
            else inspector
        )

        self._models = {}
        self._model_order = []
        self._version_order = {}

    def register_checkpoint(
        self,
        model_id,
        version,
        checkpoint_path,
        metadata=None,
        stage=False,
    ):
        self._validate_identity(
            model_id,
            version,
        )

        if metadata is None:
            metadata = {}

        if not isinstance(metadata, dict):
            raise TypeError(
                "metadata must be dict or None"
            )

        if self.contains(
            model_id,
            version,
        ):
            raise ValueError(
                "model version already registered: "
                + model_id
                + "@"
                + version
            )

        descriptor = (
            self.inspector.inspect(
                checkpoint_path
            )
        )

        combined_metadata = self._copy(
            descriptor[
                "metadata"
            ]
        )

        for key in metadata:
            combined_metadata[
                key
            ] = self._copy(
                metadata[
                    key
                ]
            )

        item = ModelVersion(
            model_id=model_id,
            version=version,
            checkpoint_path=checkpoint_path,
            checkpoint_checksum=descriptor[
                "checksum"
            ],
            checkpoint_bytes=descriptor[
                "bytes"
            ],
            parameter_count=descriptor[
                "parameter_count"
            ],
            architecture=descriptor[
                "architecture"
            ],
            metadata=combined_metadata,
            status=(
                "staged"
                if stage
                else "registered"
            ),
        )

        if model_id not in self._models:
            self._models[
                model_id
            ] = {}

            self._version_order[
                model_id
            ] = []

            self._model_order.append(
                model_id
            )

        self._models[
            model_id
        ][
            version
        ] = item

        self._version_order[
            model_id
        ].append(
            version
        )

        return item

    def contains(
        self,
        model_id,
        version,
    ):
        return (
            model_id in self._models
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
                "model version not registered: "
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
        include_deprecated=True,
    ):
        if model_id not in self._models:
            return []

        result = []

        for version in self._version_order[
            model_id
        ]:
            item = self._models[
                model_id
            ][
                version
            ]

            if (
                include_deprecated
                or item.status
                != "deprecated"
            ):
                result.append(
                    item
                )

        return result

    def models(
        self,
    ):
        result = []

        for model_id in self._model_order:
            active = self.active(
                model_id,
                required=False,
            )

            result.append({
                "model_id": model_id,
                "version_count": len(
                    self._version_order[
                        model_id
                    ]
                ),
                "active_version": (
                    None
                    if active is None
                    else active.version
                ),
                "versions": [
                    item.version
                    for item in self.versions(
                        model_id
                    )
                ],
            })

        return result

    def stage(
        self,
        model_id,
        version,
    ):
        item = self.get(
            model_id,
            version,
        )

        if item.status == "active":
            raise RuntimeError(
                "active version must be replaced before it can be staged"
            )

        return item.stage()

    def promote(
        self,
        model_id,
        version,
    ):
        item = self.get(
            model_id,
            version,
        )

        if item.status == "deprecated":
            raise RuntimeError(
                "deprecated model version cannot be promoted"
            )

        for existing in self.versions(
            model_id
        ):
            if (
                existing.status == "active"
                and existing.version
                != version
            ):
                existing.status = "staged"

        item.activate()
        return item

    def deprecate(
        self,
        model_id,
        version,
    ):
        item = self.get(
            model_id,
            version,
        )

        item.deprecate()
        return item

    def active(
        self,
        model_id,
        required=True,
    ):
        if model_id not in self._models:
            if required:
                raise KeyError(
                    "model not registered: "
                    + str(model_id)
                )

            return None

        for version in self._version_order[
            model_id
        ]:
            item = self._models[
                model_id
            ][
                version
            ]

            if item.status == "active":
                return item

        if required:
            raise KeyError(
                "no active version for model: "
                + model_id
            )

        return None

    def verify(
        self,
        model_id,
        version,
    ):
        item = self.get(
            model_id,
            version,
        )

        observed = (
            self.inspector
            .try_inspect(
                item.checkpoint_path
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
                "stored_checksum": item.checkpoint_checksum,
                "observed_checksum": None,
                "stored_bytes": item.checkpoint_bytes,
                "observed_bytes": None,
                "error": observed.get(
                    "error"
                ),
            }

        checksum_match = (
            observed[
                "checksum"
            ]
            == item.checkpoint_checksum
        )

        bytes_match = (
            observed[
                "bytes"
            ]
            == item.checkpoint_bytes
        )

        parameter_match = (
            observed[
                "parameter_count"
            ]
            == item.parameter_count
        )

        return {
            "model_id": model_id,
            "version": version,
            "valid": (
                checksum_match
                and bytes_match
                and parameter_match
            ),
            "checkpoint_valid": True,
            "checksum_match": checksum_match,
            "bytes_match": bytes_match,
            "parameter_count_match": parameter_match,
            "stored_checksum": item.checkpoint_checksum,
            "observed_checksum": observed[
                "checksum"
            ],
            "stored_bytes": item.checkpoint_bytes,
            "observed_bytes": observed[
                "bytes"
            ],
        }

    def export_state(
        self,
    ):
        return {
            "format": "SireLLMModelRegistry",
            "version": 1,
            "models": [
                {
                    "model_id": model_id,
                    "versions": [
                        item.to_dict()
                        for item in self.versions(
                            model_id
                        )
                    ],
                }
                for model_id in self._model_order
            ],
        }

    def load_state(
        self,
        state,
    ):
        if not isinstance(state, dict):
            raise TypeError(
                "registry state must be dict"
            )

        if state.get(
            "format"
        ) != "SireLLMModelRegistry":
            raise ValueError(
                "invalid model registry state format"
            )

        if int(
            state.get(
                "version",
                0,
            )
        ) != 1:
            raise ValueError(
                "unsupported model registry state version"
            )

        staged_models = {}
        staged_model_order = []
        staged_version_order = {}

        for model_row in state.get(
            "models",
            [],
        ):
            model_id = model_row[
                "model_id"
            ]

            if model_id in staged_models:
                raise ValueError(
                    "duplicate model in registry state: "
                    + model_id
                )

            staged_models[
                model_id
            ] = {}

            staged_model_order.append(
                model_id
            )

            staged_version_order[
                model_id
            ] = []

            active_count = 0

            for version_row in model_row.get(
                "versions",
                [],
            ):
                item = (
                    ModelVersion
                    .from_dict(
                        version_row
                    )
                )

                if item.model_id != model_id:
                    raise ValueError(
                        "model/version identity mismatch in registry state"
                    )

                if item.version in staged_models[
                    model_id
                ]:
                    raise ValueError(
                        "duplicate version in registry state"
                    )

                if item.status == "active":
                    active_count += 1

                staged_models[
                    model_id
                ][
                    item.version
                ] = item

                staged_version_order[
                    model_id
                ].append(
                    item.version
                )

            if active_count > 1:
                raise ValueError(
                    "registry state contains multiple active versions"
                )

        self._models = staged_models
        self._model_order = staged_model_order
        self._version_order = staged_version_order

        return self

    def _validate_identity(
        self,
        model_id,
        version,
    ):
        if not isinstance(model_id, str) or model_id == "":
            raise ValueError(
                "model_id must be non-empty str"
            )

        if not isinstance(version, str) or version == "":
            raise ValueError(
                "version must be non-empty str"
            )

    def _copy(self, value):
        if isinstance(value, dict):
            result = {}

            for key in value:
                result[key] = self._copy(
                    value[
                        key
                    ]
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
