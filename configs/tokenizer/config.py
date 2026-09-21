class TokenizerConfig:
    """
    Tokenizer bootstrap configuration.

    mode:
      train -> build byte-level BPE from runtime corpus
      load  -> load deterministic tokenizer artifact
      none  -> construct manager without initializing tokenizer
    """

    MODES = (
        "train",
        "load",
        "none",
    )

    def __init__(
        self,
        mode="train",
        training=None,
        artifact_path=None,
        persist_after_train=False,
        metadata=None,
    ):
        mode = str(
            mode
        ).lower()

        if mode not in self.MODES:
            raise ValueError(
                "unsupported tokenizer mode"
            )

        if training is None:
            training = (
                TokenizerTrainingConfig()
            )

        if not isinstance(
            training,
            TokenizerTrainingConfig,
        ):
            raise TypeError(
                "training must be TokenizerTrainingConfig or None"
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

        if (
            mode == "load"
            and artifact_path is None
        ):
            raise ValueError(
                "load mode requires artifact_path"
            )

        if (
            persist_after_train
            and mode != "train"
        ):
            raise ValueError(
                "persist_after_train requires train mode"
            )

        if (
            persist_after_train
            and artifact_path is None
        ):
            raise ValueError(
                "persist_after_train requires artifact_path"
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
        self.training = training
        self.artifact_path = (
            artifact_path
        )
        self.persist_after_train = bool(
            persist_after_train
        )
        self.metadata = self._copy(
            metadata
        )

    def to_dict(
        self,
    ):
        return {
            "mode": self.mode,
            "training": (
                self.training.to_dict()
            ),
            "artifact_path": (
                self.artifact_path
            ),
            "persist_after_train": (
                self.persist_after_train
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
