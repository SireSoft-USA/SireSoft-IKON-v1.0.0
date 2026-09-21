class ConversationWindowConfig:
    def __init__(
        self,
        context_max_tokens=256,
        rag_history_tokens=128,
    ):
        if (
            not isinstance(
                context_max_tokens,
                int,
            )
            or context_max_tokens <= 0
        ):
            raise ValueError(
                "context_max_tokens must be positive int"
            )

        if (
            not isinstance(
                rag_history_tokens,
                int,
            )
            or rag_history_tokens <= 0
        ):
            raise ValueError(
                "rag_history_tokens must be positive int"
            )

        self.context_max_tokens = (
            context_max_tokens
        )
        self.rag_history_tokens = (
            rag_history_tokens
        )

    def to_dict(
        self,
    ):
        return {
            "context_max_tokens": (
                self.context_max_tokens
            ),
            "rag_history_tokens": (
                self.rag_history_tokens
            ),
        }
