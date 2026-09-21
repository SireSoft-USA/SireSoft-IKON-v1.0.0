class EmbeddingConfigFactory:
    """
    Builds and initializes the real tokenizer-backed hashing TF-IDF embedder.
    Training text is injected at runtime instead of serialized into config.
    """

    def build_manager(
        self,
        config,
        tokenizer,
    ):
        if not isinstance(
            config,
            EmbeddingConfig,
        ):
            raise TypeError(
                "config must be EmbeddingConfig"
            )

        EmbeddingConfigValidator().require_valid(
            config
        )

        return EmbeddingManager(
            tokenizer=tokenizer,
            dimension=(
                config.model.dimension
            ),
            min_n=(
                config.model.min_n
            ),
            max_n=(
                config.model.max_n
            ),
            use_idf=(
                config.model.use_idf
            ),
            sublinear_tf=(
                config.model
                .sublinear_tf
            ),
            l2_normalize=(
                config.model
                .l2_normalize
            ),
        )

    def initialize(
        self,
        config,
        tokenizer,
        texts=None,
        texts_provider=None,
        manager=None,
    ):
        if not isinstance(
            config,
            EmbeddingConfig,
        ):
            raise TypeError(
                "config must be EmbeddingConfig"
            )

        EmbeddingConfigValidator().require_valid(
            config
        )

        if manager is None:
            manager = self.build_manager(
                config,
                tokenizer,
            )

        if not isinstance(
            manager,
            EmbeddingManager,
        ):
            raise TypeError(
                "manager must be EmbeddingManager or None"
            )

        if config.mode == "load":
            info = manager.load_state_file(
                config.artifact_path,
                expected_dimension=(
                    config
                    .expected_dimension
                    if config
                    .expected_dimension
                    is not None
                    else config
                    .model
                    .dimension
                ),
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

        if (
            texts is None
            and texts_provider
            is not None
        ):
            if not callable(
                texts_provider
            ):
                raise TypeError(
                    "texts_provider must be callable or None"
                )

            texts = texts_provider()

        if texts is None:
            raise ValueError(
                "fit mode requires texts or texts_provider"
            )

        info = manager.fit(
            texts
        )

        artifact = None

        if config.persist_after_fit:
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
            "mode": "fit",
        }

    def build_service(
        self,
        config,
        tokenizer,
        texts=None,
        texts_provider=None,
    ):
        result = self.initialize(
            config,
            tokenizer,
            texts=texts,
            texts_provider=(
                texts_provider
            ),
        )

        return EmbeddingService(
            result[
                "manager"
            ]
        )
