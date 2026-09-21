class RAGConfigFactory:
    """
    Builds the end-to-end RAG orchestrator/service from typed configuration.
    """

    def build_prompt_builder(
        self,
        config,
    ):
        if not isinstance(
            config,
            RAGConfig,
        ):
            raise TypeError(
                "config must be RAGConfig"
            )

        return PromptBuilder(
            system_message=(
                config
                .prompt
                .system_message
            ),
            compact=(
                config
                .prompt
                .compact
            ),
        )

    def build_orchestrator(
        self,
        config,
        tokenizer,
        retrieval_manager,
        inference_runtime,
        safety_engine=None,
    ):
        if not isinstance(
            config,
            RAGConfig,
        ):
            raise TypeError(
                "config must be RAGConfig"
            )

        RAGConfigValidator().require_valid(
            config,
            inference_runtime=(
                inference_runtime
            ),
        )

        return RAGServiceOrchestrator(
            tokenizer=tokenizer,
            retrieval_manager=(
                retrieval_manager
            ),
            inference_runtime=(
                inference_runtime
            ),
            safety_engine=(
                safety_engine
            ),
            max_context_tokens=(
                config
                .max_context_tokens
            ),
            prompt_builder=(
                self.build_prompt_builder(
                    config
                )
            ),
        )

    def build_service(
        self,
        config,
        tokenizer,
        retrieval_manager,
        inference_runtime,
        safety_engine=None,
    ):
        return RAGService(
            self.build_orchestrator(
                config,
                tokenizer,
                retrieval_manager,
                inference_runtime,
                safety_engine=(
                    safety_engine
                ),
            )
        )

    def prepare(
        self,
        orchestrator,
        config,
        query_text,
        filters=None,
        retrieval_overrides=None,
        max_prompt_tokens=None,
    ):
        retrieval = self._retrieval_values(
            config,
            retrieval_overrides,
        )

        if max_prompt_tokens is None:
            max_prompt_tokens = (
                config
                .max_prompt_tokens
            )

        return orchestrator.prepare(
            query_text=query_text,
            candidate_k=(
                retrieval[
                    "candidate_k"
                ]
            ),
            top_k=(
                retrieval[
                    "top_k"
                ]
            ),
            min_score=(
                retrieval[
                    "min_score"
                ]
            ),
            filters=filters,
            use_mmr=(
                retrieval[
                    "use_mmr"
                ]
            ),
            mmr_lambda=(
                retrieval[
                    "mmr_lambda"
                ]
            ),
            similarity_weight=(
                retrieval[
                    "similarity_weight"
                ]
            ),
            dataset_boosts=(
                retrieval[
                    "dataset_boosts"
                ]
            ),
            document_boosts=(
                retrieval[
                    "document_boosts"
                ]
            ),
            metadata_boosts=(
                retrieval[
                    "metadata_boosts"
                ]
            ),
            max_prompt_tokens=(
                max_prompt_tokens
            ),
            max_new_tokens=(
                config
                .generation
                .max_new_tokens
            ),
        )

    def answer(
        self,
        orchestrator,
        config,
        query_text,
        filters=None,
        retrieval_overrides=None,
        generation_overrides=None,
    ):
        retrieval = self._retrieval_values(
            config,
            retrieval_overrides,
        )

        generation = self._generation_values(
            config,
            generation_overrides,
        )

        return orchestrator.answer(
            query_text=query_text,
            max_new_tokens=(
                generation[
                    "max_new_tokens"
                ]
            ),
            candidate_k=(
                retrieval[
                    "candidate_k"
                ]
            ),
            top_k=(
                retrieval[
                    "top_k"
                ]
            ),
            min_score=(
                retrieval[
                    "min_score"
                ]
            ),
            filters=filters,
            use_mmr=(
                retrieval[
                    "use_mmr"
                ]
            ),
            mmr_lambda=(
                retrieval[
                    "mmr_lambda"
                ]
            ),
            similarity_weight=(
                retrieval[
                    "similarity_weight"
                ]
            ),
            dataset_boosts=(
                retrieval[
                    "dataset_boosts"
                ]
            ),
            document_boosts=(
                retrieval[
                    "document_boosts"
                ]
            ),
            metadata_boosts=(
                retrieval[
                    "metadata_boosts"
                ]
            ),
            eos_token_ids=(
                generation[
                    "eos_token_ids"
                ]
            ),
            sampler=(
                generation[
                    "sampler"
                ]
            ),
            seed=(
                generation[
                    "seed"
                ]
            ),
            temperature=(
                generation[
                    "temperature"
                ]
            ),
            top_k_sampling=(
                generation[
                    "top_k_sampling"
                ]
            ),
            top_p=(
                generation[
                    "top_p"
                ]
            ),
            repetition_penalty=(
                generation[
                    "repetition_penalty"
                ]
            ),
            banned_token_ids=(
                generation[
                    "banned_token_ids"
                ]
            ),
        )

    def _retrieval_values(
        self,
        config,
        overrides,
    ):
        if not isinstance(
            config,
            RAGConfig,
        ):
            raise TypeError(
                "config must be RAGConfig"
            )

        values = (
            config
            .retrieval
            .to_dict()
        )

        if overrides is not None:
            if not isinstance(
                overrides,
                dict,
            ):
                raise TypeError(
                    "retrieval_overrides must be dict or None"
                )

            for key in overrides:
                if key not in values:
                    raise ValueError(
                        "unsupported RAG retrieval override: "
                        + str(key)
                    )

                values[key] = overrides[
                    key
                ]

        validated = RAGRetrievalConfig(
            candidate_k=values[
                "candidate_k"
            ],
            top_k=values[
                "top_k"
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
            similarity_weight=values[
                "similarity_weight"
            ],
            dataset_boosts=values[
                "dataset_boosts"
            ],
            document_boosts=values[
                "document_boosts"
            ],
            metadata_boosts=values[
                "metadata_boosts"
            ],
        )

        return validated.to_dict()

    def _generation_values(
        self,
        config,
        overrides,
    ):
        values = (
            config
            .generation
            .to_dict()
        )

        if overrides is not None:
            if not isinstance(
                overrides,
                dict,
            ):
                raise TypeError(
                    "generation_overrides must be dict or None"
                )

            for key in overrides:
                if key not in values:
                    raise ValueError(
                        "unsupported RAG generation override: "
                        + str(key)
                    )

                values[key] = overrides[
                    key
                ]

        validated = RAGGenerationConfig(
            max_new_tokens=values[
                "max_new_tokens"
            ],
            eos_token_ids=values[
                "eos_token_ids"
            ],
            sampler=values[
                "sampler"
            ],
            seed=values[
                "seed"
            ],
            temperature=values[
                "temperature"
            ],
            top_k_sampling=values[
                "top_k_sampling"
            ],
            top_p=values[
                "top_p"
            ],
            repetition_penalty=values[
                "repetition_penalty"
            ],
            banned_token_ids=values[
                "banned_token_ids"
            ],
        )

        return validated.to_dict()
