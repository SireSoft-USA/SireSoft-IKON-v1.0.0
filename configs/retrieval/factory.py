class RetrievalConfigFactory:
    """
    Builds RetrievalManager/RetrievalService and applies typed index/search
    defaults without bypassing the handwritten retrieval stack.
    """

    def build_manager(
        self,
        config,
        tokenizer,
        persistence=None,
    ):
        if not isinstance(
            config,
            RetrievalConfig,
        ):
            raise TypeError(
                "config must be RetrievalConfig"
            )

        RetrievalConfigValidator().require_valid(
            config
        )

        return RetrievalManager(
            tokenizer=tokenizer,
            Document=Document,
            dimension=(
                config.embedding.dimension
            ),
            min_n=(
                config.embedding.min_n
            ),
            max_n=(
                config.embedding.max_n
            ),
            max_chars=(
                config.chunking.max_chars
            ),
            overlap_chars=(
                config.chunking
                .overlap_chars
            ),
            min_chunk_chars=(
                config.chunking
                .min_chunk_chars
            ),
            use_idf=(
                config.embedding.use_idf
            ),
            sublinear_tf=(
                config.embedding
                .sublinear_tf
            ),
            l2_normalize=(
                config.embedding
                .l2_normalize
            ),
            persistence=persistence,
        )

    def build_service(
        self,
        config,
        tokenizer,
        persistence=None,
    ):
        return RetrievalService(
            self.build_manager(
                config,
                tokenizer,
                persistence=persistence,
            )
        )

    def initialize(
        self,
        config,
        tokenizer,
        documents=None,
        persistence=None,
        load_persisted=False,
    ):
        manager = self.build_manager(
            config,
            tokenizer,
            persistence=persistence,
        )

        if (
            load_persisted
            and config.persistence_path
            is not None
        ):
            manager.load_state_file(
                config.persistence_path
            )

        elif documents is not None:
            manager.index_documents(
                documents,
                mode=(
                    config
                    .default_index_mode
                ),
                refit=(
                    config
                    .default_refit
                ),
            )

        return manager

    def search(
        self,
        manager,
        config,
        query,
        overrides=None,
    ):
        if not isinstance(
            manager,
            RetrievalManager,
        ):
            raise TypeError(
                "manager must be RetrievalManager"
            )

        if not isinstance(
            config,
            RetrievalConfig,
        ):
            raise TypeError(
                "config must be RetrievalConfig"
            )

        values = (
            config.search.to_dict()
        )

        if overrides is not None:
            if not isinstance(
                overrides,
                dict,
            ):
                raise TypeError(
                    "overrides must be dict or None"
                )

            for key in overrides:
                if key not in values:
                    raise ValueError(
                        "unsupported retrieval override: "
                        + str(
                            key
                        )
                    )

                values[
                    key
                ] = overrides[
                    key
                ]

        validated = (
            RetrievalSearchConfig(
                top_k=values[
                    "top_k"
                ],
                search_k=values[
                    "search_k"
                ],
                min_score=values[
                    "min_score"
                ],
                use_mmr=values[
                    "use_mmr"
                ],
                mmr_lambda=values[
                    "mmr_lambda"
                ],
                similarity_weight=(
                    values[
                        "similarity_weight"
                    ]
                ),
                dataset_boosts=(
                    values[
                        "dataset_boosts"
                    ]
                ),
                document_boosts=(
                    values[
                        "document_boosts"
                    ]
                ),
                metadata_boosts=(
                    values[
                        "metadata_boosts"
                    ]
                ),
            )
        )

        return manager.search(
            query=query,
            top_k=(
                validated.top_k
            ),
            search_k=(
                validated.search_k
            ),
            min_score=(
                validated.min_score
            ),
            use_mmr=(
                validated.use_mmr
            ),
            mmr_lambda=(
                validated.mmr_lambda
            ),
            similarity_weight=(
                validated
                .similarity_weight
            ),
            dataset_boosts=(
                validated
                .dataset_boosts
            ),
            document_boosts=(
                validated
                .document_boosts
            ),
            metadata_boosts=(
                validated
                .metadata_boosts
            ),
        )
