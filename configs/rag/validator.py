class RAGConfigValidator:
    def validate(
        self,
        config,
        inference_runtime=None,
    ):
        if not isinstance(
            config,
            RAGConfig,
        ):
            raise TypeError(
                "config must be RAGConfig"
            )

        errors = []
        warnings = []

        if (
            config.retrieval.candidate_k
            < config.retrieval.top_k
        ):
            warnings.append({
                "code": (
                    "CANDIDATE_K_BELOW_TOP_K"
                ),
                "message": (
                    "RAG retrieval bridge will raise candidate_k to top_k"
                ),
            })

        if (
            config.max_context_tokens
            == 0
        ):
            warnings.append({
                "code": (
                    "ZERO_CONTEXT_BUDGET"
                ),
                "message": (
                    "Retrieved sources cannot enter the prompt"
                ),
            })

        generation = (
            config.generation
        )

        if (
            generation.sampler
            == "greedy"
            and (
                generation.top_k_sampling
                is not None
                or generation.top_p
                is not None
                or generation.temperature
                != 1.0
            )
        ):
            warnings.append({
                "code": (
                    "GREEDY_WITH_SAMPLING_CONTROLS"
                ),
                "message": (
                    "Sampling controls are configured while sampler is greedy"
                ),
            })

        if inference_runtime is not None:
            if not hasattr(
                inference_runtime,
                "ready",
            ):
                raise TypeError(
                    "inference_runtime must provide ready()"
                )

            if not inference_runtime.ready():
                errors.append({
                    "code": (
                        "INFERENCE_RUNTIME_NOT_READY"
                    ),
                    "message": (
                        "RAG answer generation requires a loaded inference model"
                    ),
                })

            elif (
                config.max_prompt_tokens
                is not None
                and hasattr(
                    inference_runtime,
                    "loaded",
                )
                and inference_runtime.loaded
                is not None
                and hasattr(
                    inference_runtime.loaded,
                    "model",
                )
            ):
                model = (
                    inference_runtime
                    .loaded
                    .model
                )

                model_limit = getattr(
                    model,
                    "max_seq_len",
                    None,
                )

                if (
                    isinstance(
                        model_limit,
                        int,
                    )
                    and (
                        config.max_prompt_tokens
                        + generation.max_new_tokens
                        > model_limit
                    )
                ):
                    errors.append({
                        "code": (
                            "PROMPT_GENERATION_BUDGET_EXCEEDS_MODEL"
                        ),
                        "message": (
                            "max_prompt_tokens + max_new_tokens exceeds model max_seq_len"
                        ),
                    })

        return {
            "valid": (
                len(errors) == 0
            ),
            "error_count": len(
                errors
            ),
            "warning_count": len(
                warnings
            ),
            "errors": errors,
            "warnings": warnings,
        }

    def require_valid(
        self,
        config,
        inference_runtime=None,
    ):
        result = self.validate(
            config,
            inference_runtime=(
                inference_runtime
            ),
        )

        if not result["valid"]:
            first = result[
                "errors"
            ][0]

            raise ValueError(
                first["code"]
                + ": "
                + first["message"]
            )

        return result
