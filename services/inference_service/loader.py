class LoadedModel:
    """
    One checkpoint-backed model currently available to inference.
    """

    def __init__(
        self,
        model_id,
        version,
        registry_version,
        model,
    ):
        if not isinstance(model_id, str) or model_id == "":
            raise ValueError("model_id must be non-empty str")

        if not isinstance(version, str) or version == "":
            raise ValueError("version must be non-empty str")

        self.model_id = model_id
        self.version = version
        self.registry_version = registry_version
        self.model = model

    def info(self):
        return {
            "model_id": self.model_id,
            "version": self.version,
            "checkpoint_path": (
                self.registry_version
                .checkpoint_path
            ),
            "checkpoint_checksum": (
                self.registry_version
                .checkpoint_checksum
            ),
            "parameter_count": (
                self.model
                .parameter_count()
            ),
            "vocab_size": self.model.vocab_size,
            "d_model": self.model.d_model,
            "max_seq_len": (
                self.model.max_seq_len
            ),
            "position_mode": (
                self.model.position_mode
            ),
        }


class ModelLoader:
    """
    Builds LanguageModel from model-registry architecture metadata and restores
    exact checkpoint weights through SireLLM CheckpointManager.
    """

    REQUIRED_ARCHITECTURE = (
        "vocab_size",
        "d_model",
        "num_layers",
        "num_heads",
        "d_ff",
        "max_seq_len",
    )

    def __init__(
        self,
        registry,
        checkpoint_manager=None,
    ):
        if registry is None or not hasattr(
            registry,
            "get",
        ):
            raise TypeError(
                "registry must provide get()"
            )

        if not hasattr(
            registry,
            "verify",
        ):
            raise TypeError(
                "registry must provide verify()"
            )

        self.registry = registry
        self.checkpoint_manager = (
            CheckpointManager()
            if checkpoint_manager is None
            else checkpoint_manager
        )

    def load_active(
        self,
        model_id,
    ):
        item = self.registry.active(
            model_id
        )

        return self.load_version(
            model_id,
            item.version,
        )

    def load_version(
        self,
        model_id,
        version,
    ):
        item = self.registry.get(
            model_id,
            version,
        )

        verification = (
            self.registry.verify(
                model_id,
                version,
            )
        )

        if not verification.get(
            "valid",
            False,
        ):
            raise ValueError(
                "registered checkpoint failed integrity verification"
            )

        architecture = (
            item.architecture
        )

        self._validate_architecture(
            architecture
        )

        model = LanguageModel(
            vocab_size=int(
                architecture[
                    "vocab_size"
                ]
            ),
            d_model=int(
                architecture[
                    "d_model"
                ]
            ),
            num_layers=int(
                architecture[
                    "num_layers"
                ]
            ),
            num_heads=int(
                architecture[
                    "num_heads"
                ]
            ),
            d_ff=int(
                architecture[
                    "d_ff"
                ]
            ),
            max_seq_len=int(
                architecture[
                    "max_seq_len"
                ]
            ),
            dropout=float(
                architecture.get(
                    "dropout",
                    0.0,
                )
            ),
            position_mode=architecture.get(
                "position_mode",
                "rotary",
            ),
            padding_idx=architecture.get(
                "padding_idx"
            ),
            seed=int(
                architecture.get(
                    "seed",
                    1337,
                )
            ),
        )

        self.checkpoint_manager.load(
            path=item.checkpoint_path,
            model=model,
            strict_model=True,
        )

        model.eval()

        if (
            model.parameter_count()
            != item.parameter_count
        ):
            raise ValueError(
                "loaded model parameter count does not match registry"
            )

        return LoadedModel(
            model_id=model_id,
            version=version,
            registry_version=item,
            model=model,
        )

    def _validate_architecture(
        self,
        architecture,
    ):
        if not isinstance(
            architecture,
            dict,
        ):
            raise ValueError(
                "registered model architecture must be dict"
            )

        for key in self.REQUIRED_ARCHITECTURE:
            if key not in architecture:
                raise ValueError(
                    "registered model architecture missing "
                    + key
                )

            value = architecture[
                key
            ]

            if (
                not isinstance(
                    value,
                    int,
                )
                or value <= 0
            ):
                raise ValueError(
                    "registered model architecture "
                    + key
                    + " must be positive int"
                )
