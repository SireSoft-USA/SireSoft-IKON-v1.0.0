class ModelManifest:
    """
    Immutable deployment/storage manifest for one model version.

    It references a checkpoint artifact and captures architecture/runtime
    metadata without embedding parameter tensors themselves.
    """

    FORMAT = "SireLLMModelManifest"
    SCHEMA_VERSION = 1

    def __init__(
        self,
        model_id,
        version,
        created_at,
        checkpoint,
        architecture=None,
        tokenizer=None,
        runtime=None,
        metadata=None,
    ):
        for field_name, value in (
            ("model_id", model_id),
            ("version", version),
        ):
            if not isinstance(value, str) or value == "":
                raise ValueError(
                    field_name + " must be non-empty str"
                )

        if (
            not isinstance(created_at, int)
            or created_at < 0
        ):
            raise ValueError(
                "created_at must be non-negative int"
            )

        if not isinstance(checkpoint, dict):
            raise TypeError(
                "checkpoint must be dict"
            )

        required_checkpoint = (
            "path",
            "checksum",
            "byte_count",
            "parameter_count",
            "parameter_tensors",
        )

        for key in required_checkpoint:
            if key not in checkpoint:
                raise ValueError(
                    "checkpoint requires "
                    + key
                )

        if architecture is None:
            architecture = {}

        if tokenizer is None:
            tokenizer = {}

        if runtime is None:
            runtime = {}

        if metadata is None:
            metadata = {}

        for field_name, value in (
            ("architecture", architecture),
            ("tokenizer", tokenizer),
            ("runtime", runtime),
            ("metadata", metadata),
        ):
            if not isinstance(value, dict):
                raise TypeError(
                    field_name
                    + " must be dict or None"
                )

        self.model_id = model_id
        self.version = version
        self.created_at = created_at
        self.checkpoint = self._copy(
            checkpoint
        )
        self.architecture = self._copy(
            architecture
        )
        self.tokenizer = self._copy(
            tokenizer
        )
        self.runtime = self._copy(
            runtime
        )
        self.metadata = self._copy(
            metadata
        )

    def key(
        self,
    ):
        return (
            self.model_id
            + "@"
            + self.version
        )

    def to_dict(
        self,
    ):
        return {
            "format": self.FORMAT,
            "schema_version": (
                self.SCHEMA_VERSION
            ),
            "model_id": self.model_id,
            "version": self.version,
            "created_at": (
                self.created_at
            ),
            "checkpoint": (
                self._copy(
                    self.checkpoint
                )
            ),
            "architecture": (
                self._copy(
                    self.architecture
                )
            ),
            "tokenizer": (
                self._copy(
                    self.tokenizer
                )
            ),
            "runtime": (
                self._copy(
                    self.runtime
                )
            ),
            "metadata": (
                self._copy(
                    self.metadata
                )
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
                "model manifest state must be dict"
            )

        if value.get(
            "format"
        ) != cls.FORMAT:
            raise ValueError(
                "invalid model manifest format"
            )

        if int(
            value.get(
                "schema_version",
                0,
            )
        ) != cls.SCHEMA_VERSION:
            raise ValueError(
                "unsupported model manifest schema version"
            )

        return cls(
            model_id=value[
                "model_id"
            ],
            version=value[
                "version"
            ],
            created_at=int(
                value[
                    "created_at"
                ]
            ),
            checkpoint=value[
                "checkpoint"
            ],
            architecture=value.get(
                "architecture",
                {},
            ),
            tokenizer=value.get(
                "tokenizer",
                {},
            ),
            runtime=value.get(
                "runtime",
                {},
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
