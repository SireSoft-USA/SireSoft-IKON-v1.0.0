class PreparedRAGRequest:
    def __init__(
        self,
        query_text,
        retrieval,
        context,
        prompt,
        prompt_ids,
    ):
        self.query_text = query_text
        self.retrieval = retrieval
        self.context = context
        self.prompt = prompt
        self.prompt_ids = list(prompt_ids)

    def prompt_token_count(self):
        return len(self.prompt_ids)

    def to_dict(self):
        return {
            "query_text": self.query_text,
            "prompt": self.prompt,
            "prompt_token_count": self.prompt_token_count(),
            "context": self.context.to_dict(),
            "retrieval": self.retrieval.to_dict(),
        }


class RAGResult:
    def __init__(
        self,
        prepared,
        answer_text,
        generated_ids,
        stop_reason,
    ):
        self.prepared = prepared
        self.query_text = prepared.query_text
        self.answer_text = answer_text
        self.generated_ids = list(generated_ids)
        self.stop_reason = stop_reason
        self.citations = list(
            prepared.context.citations
        )

    def to_dict(self):
        return {
            "query_text": self.query_text,
            "answer_text": self.answer_text,
            "generated_ids": list(self.generated_ids),
            "stop_reason": self.stop_reason,
            "citations": [
                citation.to_dict()
                for citation in self.citations
            ],
        }
