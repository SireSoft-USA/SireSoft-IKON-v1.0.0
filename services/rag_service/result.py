class RAGPreparation:
    """
    Internal prepared RAG request.

    The prompt itself remains internal unless explicitly requested for debugging.
    """

    def __init__(
        self,
        query_text,
        status,
        blocked_phase,
        retrieval,
        context,
        prompt,
        prompt_ids,
        input_decision,
        context_decision,
        safety_view,
    ):
        self.query_text = query_text
        self.status = status
        self.blocked_phase = (
            blocked_phase
        )
        self.retrieval = retrieval
        self.context = context
        self.prompt = prompt
        self.prompt_ids = list(
            prompt_ids
        )
        self.input_decision = (
            input_decision
        )
        self.context_decision = (
            context_decision
        )
        self.safety_view = safety_view

    def ready(
        self,
    ):
        return self.status == "ready"

    def prompt_token_count(
        self,
    ):
        return len(
            self.prompt_ids
        )

    def citations(
        self,
    ):
        if self.context is None:
            return []

        return list(
            self.context.citations
        )

    def to_dict(
        self,
        include_prompt=False,
    ):
        result = {
            "status": self.status,
            "blocked_phase": (
                self.blocked_phase
            ),
            "query_text": (
                self.query_text
            ),
            "prompt_token_count": (
                self.prompt_token_count()
            ),
            "retrieval": {
                "raw_count": (
                    0
                    if self.retrieval is None
                    else len(
                        self.retrieval
                        .raw_results
                    )
                ),
                "ranked_count": (
                    0
                    if self.retrieval is None
                    else len(
                        self.retrieval
                        .ranked_results
                    )
                ),
            },
            "context": {
                "token_count": (
                    0
                    if self.context is None
                    else self.context.token_count
                ),
                "source_count": (
                    0
                    if self.context is None
                    else self.context.source_count()
                ),
                "skipped_item_ids": (
                    []
                    if self.context is None
                    else list(
                        self.context
                        .skipped_item_ids
                    )
                ),
            },
            "citations": [
                citation.to_dict()
                for citation in self.citations()
            ] if self.ready() else [],
            "safety": {
                "input": (
                    self.safety_view
                    .decision(
                        self.input_decision
                    )
                ),
                "context": (
                    self.safety_view
                    .decision(
                        self.context_decision
                    )
                ),
            },
        }

        if include_prompt:
            result[
                "prompt"
            ] = self.prompt

            result[
                "prompt_ids"
            ] = list(
                self.prompt_ids
            )

        return result


class RAGServiceResult:
    """
    Public answer object with output-leakage-safe blocking semantics.
    """

    def __init__(
        self,
        preparation,
        answer_text,
        generated_ids,
        generated_count,
        stop_reason,
        output_decision,
        safety_view,
        status="ok",
        blocked_phase=None,
    ):
        self.preparation = (
            preparation
        )
        self.answer_text = (
            answer_text
        )
        self.generated_ids = list(
            generated_ids
        )
        self.generated_count = int(
            generated_count
        )
        self.stop_reason = (
            stop_reason
        )
        self.output_decision = (
            output_decision
        )
        self.safety_view = (
            safety_view
        )
        self.status = status
        self.blocked_phase = (
            blocked_phase
        )

    def to_dict(
        self,
    ):
        citations = []

        if (
            self.preparation is not None
            and self.preparation.ready()
        ):
            citations = [
                citation.to_dict()
                for citation
                in self.preparation
                .citations()
            ]

        return {
            "status": self.status,
            "blocked_phase": (
                self.blocked_phase
            ),
            "query_text": (
                None
                if self.preparation
                is None
                else self.preparation
                .query_text
            ),
            "answer_text": (
                self.answer_text
            ),
            "generated_ids": list(
                self.generated_ids
            ),
            "generated_count": (
                self.generated_count
            ),
            "stop_reason": (
                self.stop_reason
            ),
            "citations": citations,
            "prompt_token_count": (
                0
                if self.preparation
                is None
                else self.preparation
                .prompt_token_count()
            ),
            "context_token_count": (
                0
                if self.preparation
                is None
                or self.preparation
                .context
                is None
                else self.preparation
                .context
                .token_count
            ),
            "safety": {
                "input": (
                    None
                    if self.preparation
                    is None
                    else self.safety_view
                    .decision(
                        self.preparation
                        .input_decision
                    )
                ),
                "context": (
                    None
                    if self.preparation
                    is None
                    else self.safety_view
                    .decision(
                        self.preparation
                        .context_decision
                    )
                ),
                "output": (
                    self.safety_view
                    .decision(
                        self.output_decision
                    )
                ),
            },
        }
