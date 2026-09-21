class EmbeddingConfig:
    """
    Embedding startup configuration.

    mode:
      fit  -> fit IDF from runtime texts and optionally persist the state
      load -> restore persisted deterministic embedding state
      none -> configure the embedder without fitting IDF
    """

    MODES = (
        "fit",
        "load",
        "none",
    )

    def __init__(
        self,
        mode="fit",
        model=None,
        artifact_path=None,
        persist_after_fit=False,
        expected_dimension=None,
        metadata=None,
    ):
        mode = str(
            mode
        ).lower()

        if mode not in self.MODES:
            raise ValueError(
                "unsupported embedding mode"
            )

        if model is None:
            model = (
                EmbeddingModelConfig()
            )

        if not isinstance(
            model,
            EmbeddingModelConfig,
        ):
            raise TypeError(
                "model must be EmbeddingModelConfig or None"
            )

        if artifact_path is not None and (
            not isinstance(
                artifact_path,
                str,
            )
            or artifact_path == ""
        ):
            raise ValueError(
                "artifact_path must be non-empty str or None"
            )

        if expected_dimension is not None and (
            not isinstance(
                expected_dimension,
                int,
            )
            or expected_dimension <= 0
        ):
            raise ValueError(
                "expected_dimension must be positive int or None"
            )

        if (
            mode == "load"
            and artifact_path is None
        ):
            raise ValueError(
                "load mode requires artifact_path"
            )

        if (
            persist_after_fit
            and mode != "fit"
        ):
            raise ValueError(
                "persist_after_fit requires fit mode"
            )

        if (
            persist_after_fit
            and artifact_path is None
        ):
            raise ValueError(
                "persist_after_fit requires artifact_path"
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

        self.mode = mode
        self.model = model
        self.artifact_path = (
            artifact_path
        )
        self.persist_after_fit = bool(
            persist_after_fit
        )
        self.expected_dimension = (
            expected_dimension
        )
        self.metadata = self._copy(
            metadata
        )

    def to_dict(
        self,
    ):
        return {
            "mode": self.mode,
            "model": (
                self.model.to_dict()
            ),
            "artifact_path": (
                self.artifact_path
            ),
            "persist_after_fit": (
                self.persist_after_fit
            ),
            "expected_dimension": (
                self.expected_dimension
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
