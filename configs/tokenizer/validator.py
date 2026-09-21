class TokenizerConfigValidator:
    def validate(
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

        errors = []
        warnings = []

        special_tokens = (
            config
            .training
            .effective_special_tokens()
        )

        required_runtime = (
            "<BOS>",
            "<EOS>",
            "<PAD>",
            "<UNK>",
        )

        for token in required_runtime:
            if token not in special_tokens:
                warnings.append({
                    "code": (
                        "MISSING_RUNTIME_SPECIAL_TOKEN"
                    ),
                    "token": token,
                    "message": (
                        "Some runtime paths may require this special token"
                    ),
                })

        if (
            config.training.vocab_size
            < (
                256
                + len(
                    special_tokens
                )
            )
        ):
            warnings.append({
                "code": (
                    "VOCAB_TARGET_BELOW_BYTE_PLUS_SPECIAL_COUNT"
                ),
                "message": (
                    "Trainer will preserve all byte tokens and special tokens even if target is smaller"
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
            "special_token_count": len(
                special_tokens
            ),
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
