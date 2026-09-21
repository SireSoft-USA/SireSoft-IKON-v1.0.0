class RAGConfig:
    def __init__(
        self,
        retrieval=None,
        generation=None,
        prompt=None,
        max_context_tokens=512,
        max_prompt_tokens=None,
        metadata=None,
    ):
        if retrieval is None:
            retrieval = (
                RAGRetrievalConfig()
            )

        if generation is None:
            generation = (
                RAGGenerationConfig()
            )

        if prompt is None:
            prompt = (
                RAGPromptConfig()
            )

        if not isinstance(
            retrieval,
            RAGRetrievalConfig,
        ):
            raise TypeError(
                "retrieval must be RAGRetrievalConfig"
            )

        if not isinstance(
            generation,
            RAGGenerationConfig,
        ):
            raise TypeError(
                "generation must be RAGGenerationConfig"
            )

        if not isinstance(
            prompt,
            RAGPromptConfig,
        ):
            raise TypeError(
                "prompt must be RAGPromptConfig"
            )

        if (
            not isinstance(
                max_context_tokens,
                int,
            )
            or max_context_tokens < 0
        ):
            raise ValueError(
                "max_context_tokens must be non-negative int"
            )

        if max_prompt_tokens is not None and (
            not isinstance(
                max_prompt_tokens,
                int,
            )
            or max_prompt_tokens <= 0
        ):
            raise ValueError(
                "max_prompt_tokens must be positive int or None"
            )

        if metadata is None:
            metadata = {}

        if not isinstance(metadata, dict):
            raise TypeError(
                "metadata must be dict or None"
            )

        self.retrieval = retrieval
        self.generation = generation
        self.prompt = prompt
        self.max_context_tokens = (
            max_context_tokens
        )
        self.max_prompt_tokens = (
            max_prompt_tokens
        )
        self.metadata = self._copy(
            metadata
        )

    def to_dict(self):
        return {
            "retrieval": (
                self.retrieval.to_dict()
            ),
            "generation": (
                self.generation.to_dict()
            ),
            "prompt": (
                self.prompt.to_dict()
            ),
            "max_context_tokens": (
                self.max_context_tokens
            ),
            "max_prompt_tokens": (
                self.max_prompt_tokens
            ),
            "metadata": self._copy(
                self.metadata
            ),
        }

    def _copy(self, value):
        if isinstance(value, dict):
            return {
                key: self._copy(value[key])
                for key in value
            }

        if isinstance(value, (list, tuple)):
            return [
                self._copy(item)
                for item in value
            ]

        return value
