class TokenizerConfigFactory:
    """
    Builds and initializes the real handwritten byte-level BPE tokenizer
    service. Training corpus is supplied at runtime rather than serialized into
    config.
    """

    def build_manager(
        self,
        config,
    ):
        if not isinstance(
            config,
            TokenizerConfig,
        ):
            raise TypeError(
                "config must be TokenizerConfig"
            )

        TokenizerConfigValidator().require_valid(
            config
        )

        return build_tokenizer_manager()

    def build_service(
        self,
        config,
        corpus=None,
        corpus_provider=None,
    ):
        result = self.initialize(
            config,
            corpus=corpus,
            corpus_provider=(
                corpus_provider
            ),
        )

        return TokenizerService(
            result[
                "manager"
            ]
        )

    def initialize(
        self,
        config,
        corpus=None,
        corpus_provider=None,
        manager=None,
    ):
        if not isinstance(
            config,
            TokenizerConfig,
        ):
            raise TypeError(
                "config must be TokenizerConfig"
            )

        TokenizerConfigValidator().require_valid(
            config
        )

        if manager is None:
            manager = self.build_manager(
                config
            )

        if not isinstance(
            manager,
            TokenizerManager,
        ):
            raise TypeError(
                "manager must be TokenizerManager or None"
            )

        artifact = None

        if config.mode == "load":
            info = manager.load_state_file(
                config.artifact_path
            )

            return {
                "manager": manager,
                "info": info,
                "artifact": None,
                "mode": "load",
            }

        if config.mode == "none":
            return {
                "manager": manager,
                "info": manager.info(),
                "artifact": None,
                "mode": "none",
            }

        if corpus is None and corpus_provider is not None:
            if not callable(
                corpus_provider
            ):
                raise TypeError(
                    "corpus_provider must be callable or None"
                )

            corpus = corpus_provider()

        if corpus is None:
            raise ValueError(
                "train mode requires corpus or corpus_provider"
            )

        info = manager.train(
            corpus=corpus,
            vocab_size=(
                config
                .training
                .vocab_size
            ),
            min_frequency=(
                config
                .training
                .min_frequency
            ),
            special_tokens=(
                config
                .training
                .special_tokens
            ),
        )

        if config.persist_after_train:
            artifact = (
                manager
                .save_state_file(
                    config.artifact_path
                )
            )

        return {
            "manager": manager,
            "info": info,
            "artifact": artifact,
            "mode": "train",
        }
