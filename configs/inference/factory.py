class InferenceConfigFactory:
    """
    Builds the real checkpoint-backed inference runtime/service and applies
    typed generation defaults.
    """

    def build_runtime(
        self,
        config,
        registry,
        checkpoint_manager=None,
    ):
        if not isinstance(
            config,
            InferenceConfig,
        ):
            raise TypeError(
                "config must be InferenceConfig"
            )

        InferenceConfigValidator().require_valid(
            config,
            registry=registry,
        )

        loader = ModelLoader(
            registry=registry,
            checkpoint_manager=(
                checkpoint_manager
            ),
        )

        runtime = InferenceRuntime(
            loader
        )

        if config.load_mode == "active":
            runtime.load_active(
                config.model_id
            )

        elif config.load_mode == "version":
            runtime.load_version(
                config.model_id,
                config.version,
            )

        return runtime

    def build_service(
        self,
        config,
        registry,
        checkpoint_manager=None,
    ):
        return InferenceService(
            self.build_runtime(
                config,
                registry,
                checkpoint_manager=(
                    checkpoint_manager
                ),
            )
        )

    def generation_kwargs(
        self,
        config,
        overrides=None,
    ):
        if not isinstance(
            config,
            InferenceConfig,
        ):
            raise TypeError(
                "config must be InferenceConfig"
            )

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
                    "overrides must be dict or None"
                )

            for key in overrides:
                if key not in values:
                    raise ValueError(
                        "unsupported generation override: "
                        + str(
                            key
                        )
                    )

                values[
                    key
                ] = overrides[
                    key
                ]

        validated = GenerationConfig(
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
            top_k=values[
                "top_k"
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
            allow_prompt_truncation=values[
                "allow_prompt_truncation"
            ],
        )

        return validated.to_dict()

    def generate(
        self,
        runtime,
        config,
        prompt_ids,
        overrides=None,
    ):
        if not isinstance(
            runtime,
            InferenceRuntime,
        ):
            raise TypeError(
                "runtime must be InferenceRuntime"
            )

        values = self.generation_kwargs(
            config,
            overrides=overrides,
        )

        return runtime.generate(
            prompt_ids=prompt_ids,
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
            top_k=values[
                "top_k"
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
            allow_prompt_truncation=values[
                "allow_prompt_truncation"
            ],
        )
