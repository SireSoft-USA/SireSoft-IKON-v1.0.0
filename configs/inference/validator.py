class InferenceConfigValidator:
    def validate(
        self,
        config,
        registry=None,
    ):
        if not isinstance(
            config,
            InferenceConfig,
        ):
            raise TypeError(
                "config must be InferenceConfig"
            )

        errors = []
        warnings = []

        generation = (
            config.generation
        )

        overlap = {}

        for token_id in (
            generation.eos_token_ids
        ):
            if token_id in (
                generation
                .banned_token_ids
            ):
                overlap[
                    token_id
                ] = True

        if len(
            overlap
        ) > 0:
            warnings.append({
                "code": (
                    "EOS_TOKEN_IS_BANNED"
                ),
                "token_ids": sorted(
                    overlap.keys()
                ),
                "message": (
                    "One or more EOS token IDs are also banned"
                ),
            })

        if (
            generation.sampler
            == "greedy"
            and (
                generation.top_k
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

        if (
            generation.max_new_tokens
            > 4096
        ):
            warnings.append({
                "code": (
                    "VERY_LARGE_GENERATION_LIMIT"
                ),
                "message": (
                    "max_new_tokens is unusually large"
                ),
            })

        if registry is not None:
            if not hasattr(
                registry,
                "get",
            ) or not hasattr(
                registry,
                "active",
            ):
                raise TypeError(
                    "registry must provide get() and active()"
                )

            try:
                if (
                    config.load_mode
                    == "active"
                ):
                    registry.active(
                        config.model_id
                    )

                elif (
                    config.load_mode
                    == "version"
                ):
                    registry.get(
                        config.model_id,
                        config.version,
                    )

            except (
                KeyError,
                RuntimeError,
            ) as error:
                errors.append({
                    "code": (
                        "MODEL_LOAD_TARGET_UNAVAILABLE"
                    ),
                    "message": str(
                        error
                    ),
                })

        return {
            "valid": (
                len(
                    errors
                )
                == 0
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
        registry=None,
    ):
        result = self.validate(
            config,
            registry=registry,
        )

        if not result[
            "valid"
        ]:
            first = result[
                "errors"
            ][
                0
            ]

            raise ValueError(
                first[
                    "code"
                ]
                + ": "
                + first[
                    "message"
                ]
            )

        return result
