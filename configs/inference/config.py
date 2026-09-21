class InferenceConfig:
    """
    Model-load and generation defaults for the inference runtime.
    """

    LOAD_MODES = (
        "active",
        "version",
        "none",
    )

    def __init__(
        self,
        model_id,
        load_mode="active",
        version=None,
        generation=None,
        metadata=None,
    ):
        if not isinstance(
            model_id,
            str,
        ) or model_id == "":
            raise ValueError(
                "model_id must be non-empty str"
            )

        load_mode = str(
            load_mode
        ).lower()

        if load_mode not in self.LOAD_MODES:
            raise ValueError(
                "unsupported load_mode"
            )

        if load_mode == "version":
            if not isinstance(
                version,
                str,
            ) or version == "":
                raise ValueError(
                    "version load_mode requires non-empty version"
                )

        elif version is not None:
            if not isinstance(
                version,
                str,
            ) or version == "":
                raise ValueError(
                    "version must be non-empty str or None"
                )

        if generation is None:
            generation = (
                GenerationConfig()
            )

        if not isinstance(
            generation,
            GenerationConfig,
        ):
            raise TypeError(
                "generation must be GenerationConfig or None"
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

        self.model_id = model_id
        self.load_mode = load_mode
        self.version = version
        self.generation = generation
        self.metadata = self._copy(
            metadata
        )

    def to_dict(
        self,
    ):
        return {
            "model_id": self.model_id,
            "load_mode": (
                self.load_mode
            ),
            "version": self.version,
            "generation": (
                self.generation.to_dict()
            ),
            "metadata": self._copy(
                self.metadata
            ),
        }

    def _copy(
        self,
        value,
    ):
        if isinstance(
            value,
            dict,
        ):
            return {
                key: self._copy(
                    value[
                        key
                    ]
                )
                for key
                in value
            }

        if isinstance(
            value,
            (list, tuple),
        ):
            return [
                self._copy(
                    item
                )
                for item
                in value
            ]

        return value
