class RAGPipeline:
    """
    Complete SireLLM RAG orchestration.

    retrieve -> rank -> context budget -> citations -> prompt -> tokenize
             -> optional autoregressive generation

    Prompt budgeting removes the lowest-ranked whole context blocks first.
    Source chunks are never silently truncated mid-evidence.
    """

    def __init__(
        self,
        tokenizer,
        retriever,
        context_builder,
        prompt_builder,
        generator=None,
    ):
        if tokenizer is None or not hasattr(tokenizer, "encode"):
            raise TypeError("tokenizer must provide encode()")

        if not hasattr(tokenizer, "decode"):
            raise TypeError("tokenizer must provide decode()")

        if retriever is None or not hasattr(retriever, "retrieve"):
            raise TypeError("retriever must provide retrieve()")

        if context_builder is None or not hasattr(
            context_builder,
            "build",
        ):
            raise TypeError(
                "context_builder must provide build()"
            )

        if prompt_builder is None or not hasattr(
            prompt_builder,
            "build",
        ):
            raise TypeError(
                "prompt_builder must provide build()"
            )

        if generator is not None and not hasattr(
            generator,
            "generate",
        ):
            raise TypeError(
                "generator must provide generate()"
            )

        self.tokenizer = tokenizer
        self.retriever = retriever
        self.context_builder = context_builder
        self.prompt_builder = prompt_builder
        self.generator = generator

    def prepare(
        self,
        query_text,
        candidate_k=20,
        top_k=5,
        min_score=None,
        filters=None,
        use_mmr=True,
        max_prompt_tokens=None,
    ):
        retrieval = self.retriever.retrieve(
            query_text=query_text,
            candidate_k=candidate_k,
            top_k=top_k,
            min_score=min_score,
            filters=filters,
            use_mmr=use_mmr,
        )

        active_results = list(
            retrieval.ranked_results
        )

        while True:
            context = self.context_builder.build(
                active_results
            )

            prompt = self.prompt_builder.build(
                query_text,
                context,
            )

            prompt_ids = self.tokenizer.encode(
                prompt
            )

            if (
                max_prompt_tokens is None
                or len(prompt_ids) <= max_prompt_tokens
            ):
                break

            if len(active_results) == 0:
                raise ValueError(
                    "base RAG prompt exceeds available prompt token budget"
                )

            active_results = active_results[:-1]

        retrieval_for_prompt = RetrievalBundle(
            query_text=retrieval.query_text,
            query_embedding=retrieval.query_embedding,
            raw_results=retrieval.raw_results,
            ranked_results=active_results,
        )

        return PreparedRAGRequest(
            query_text=query_text,
            retrieval=retrieval_for_prompt,
            context=context,
            prompt=prompt,
            prompt_ids=prompt_ids,
        )

    def generate(
        self,
        query_text,
        max_new_tokens=64,
        candidate_k=20,
        top_k=5,
        min_score=None,
        filters=None,
        use_mmr=True,
        eos_token_ids=None,
    ):
        if self.generator is None:
            raise RuntimeError(
                "RAG generation requires a configured generator"
            )

        if not isinstance(max_new_tokens, int) or max_new_tokens < 0:
            raise ValueError(
                "max_new_tokens must be non-negative int"
            )

        max_prompt_tokens = None

        context_window = getattr(
            self.generator,
            "context_window",
            None,
        )

        if context_window is not None:
            max_prompt_tokens = (
                context_window
                - max_new_tokens
            )

            if max_prompt_tokens <= 0:
                raise ValueError(
                    "generation token request leaves no prompt capacity"
                )

        prepared = self.prepare(
            query_text=query_text,
            candidate_k=candidate_k,
            top_k=top_k,
            min_score=min_score,
            filters=filters,
            use_mmr=use_mmr,
            max_prompt_tokens=max_prompt_tokens,
        )

        state = self.generator.generate(
            prompt_ids=prepared.prompt_ids,
            max_new_tokens=max_new_tokens,
            eos_token_ids=eos_token_ids,
        )

        answer_text = self._safe_decode(
            state.generated_ids
        )

        return RAGResult(
            prepared=prepared,
            answer_text=answer_text,
            generated_ids=state.generated_ids,
            stop_reason=state.stop_reason,
        )

    def _safe_decode(self, token_ids):
        """
        Byte-BPE generation may end on an incomplete UTF-8 byte sequence.
        Preserve raw token IDs and decode the longest valid generated prefix.
        """
        end = len(token_ids)

        while end >= 0:
            try:
                return self.tokenizer.decode(
                    token_ids[:end],
                    skip_special=True,
                )

            except ValueError:
                end -= 1

        return ""
