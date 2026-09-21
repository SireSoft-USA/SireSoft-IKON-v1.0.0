class RetrievalConfigValidator:
    def validate(
        self,
        config,
    ):
        if not isinstance(
            config,
            RetrievalConfig,
        ):
            raise TypeError(
                "config must be RetrievalConfig"
            )

        errors = []
        warnings = []

        if (
            config.search.search_k
            is not None
            and config.search.search_k
            < config.search.top_k
        ):
            warnings.append({
                "code": (
                    "SEARCH_K_BELOW_TOP_K"
                ),
                "message": (
                    "RetrievalManager will raise search_k to top_k"
                ),
            })

        if (
            config.embedding.dimension
            < 64
        ):
            warnings.append({
                "code": (
                    "LOW_EMBEDDING_DIMENSION"
                ),
                "message": (
                    "Small hashing dimension may increase feature collisions"
                ),
            })

        if (
            config.chunking.overlap_chars
            > (
                config.chunking.max_chars
                // 2
            )
        ):
            warnings.append({
                "code": (
                    "HIGH_CHUNK_OVERLAP"
                ),
                "message": (
                    "Chunk overlap exceeds half the chunk size"
                ),
            })

        if (
            not config.embedding.use_idf
            and config.default_refit
        ):
            warnings.append({
                "code": (
                    "REFIT_WITHOUT_IDF"
                ),
                "message": (
                    "default_refit has limited effect when IDF is disabled"
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
