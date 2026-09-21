class ConversationConfigValidator:
    def validate(
        self,
        config,
    ):
        if not isinstance(
            config,
            ConversationConfig,
        ):
            raise TypeError(
                "config must be ConversationConfig"
            )

        errors = []
        warnings = []

        if (
            config
            .window
            .rag_history_tokens
            >
            config
            .window
            .context_max_tokens
        ):
            warnings.append({
                "code": (
                    "RAG_HISTORY_EXCEEDS_CONTEXT_DEFAULT"
                ),
                "message": (
                    "RAG history budget is larger than the default direct context budget"
                ),
            })

        if (
            config
            .window
            .context_max_tokens
            > 8192
        ):
            warnings.append({
                "code": (
                    "VERY_LARGE_CONVERSATION_WINDOW"
                ),
                "message": (
                    "Conversation history window is unusually large"
                ),
            })

        if (
            config
            .defaults
            .system_message
            is not None
            and len(
                config
                .defaults
                .system_message
            )
            > 4000
        ):
            warnings.append({
                "code": (
                    "VERY_LARGE_DEFAULT_SYSTEM_MESSAGE"
                ),
                "message": (
                    "Default system message may consume substantial model context"
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
