class EmbeddingConfigValidator:
    def validate(
        self,
        config,
    ):
        if not isinstance(
            config,
            EmbeddingConfig,
        ):
            raise TypeError(
                "config must be EmbeddingConfig"
            )

        errors = []
        warnings = []

        if (
            config.expected_dimension
            is not None
            and config.mode != "load"
        ):
            warnings.append({
                "code": (
                    "EXPECTED_DIMENSION_UNUSED"
                ),
                "message": (
                    "expected_dimension is only enforced while loading an artifact"
                ),
            })

        if (
            config.model.dimension < 64
        ):
            warnings.append({
                "code": (
                    "LOW_EMBEDDING_DIMENSION"
                ),
                "message": (
                    "Small hashing dimensions may increase lexical feature collisions"
                ),
            })

        if (
            not config.model.use_idf
            and config.mode == "fit"
        ):
            warnings.append({
                "code": (
                    "FIT_WITH_IDF_DISABLED"
                ),
                "message": (
                    "Fitting is allowed, but IDF weights will not be used during embedding"
                ),
            })

        if (
            config.mode == "none"
            and config.artifact_path
            is not None
        ):
            warnings.append({
                "code": (
                    "UNUSED_ARTIFACT_PATH"
                ),
                "message": (
                    "artifact_path is unused in none mode"
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
    ):
        result = self.validate(
            config
        )

        if not result[
            "valid"
        ]:
            first = result[
                "errors"
            ][0]

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
