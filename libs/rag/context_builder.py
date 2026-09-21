class ContextPackage:
    """
    Token-budgeted retrieved context plus its source citations.
    """

    def __init__(
        self,
        text,
        citations,
        token_count,
        skipped_item_ids=None,
    ):
        self.text = text
        self.citations = list(citations)
        self.token_count = int(token_count)
        self.skipped_item_ids = (
            []
            if skipped_item_ids is None
            else list(skipped_item_ids)
        )

    def source_count(self):
        return len(self.citations)

    def to_dict(self):
        return {
            "text": self.text,
            "token_count": self.token_count,
            "source_count": self.source_count(),
            "skipped_item_ids": list(self.skipped_item_ids),
            "citations": [
                citation.to_dict()
                for citation in self.citations
            ],
        }


class ContextBuilder:
    """
    Builds retrieved context without truncating source chunks mid-document.

    Whole chunks are admitted in ranking order until the configured token budget
    is exhausted. This preserves exact evidence and citation fidelity.
    """

    def __init__(
        self,
        tokenizer,
        max_context_tokens=512,
        citation_builder=None,
    ):
        if tokenizer is None or not hasattr(tokenizer, "encode"):
            raise TypeError("tokenizer must provide encode()")

        if not isinstance(max_context_tokens, int) or max_context_tokens < 0:
            raise ValueError("max_context_tokens must be non-negative int")

        self.tokenizer = tokenizer
        self.max_context_tokens = max_context_tokens
        self.citation_builder = (
            CitationBuilder()
            if citation_builder is None
            else citation_builder
        )

        if not hasattr(self.citation_builder, "build"):
            raise TypeError("citation_builder must provide build()")

    def build(
        self,
        ranked_results,
        max_context_tokens=None,
    ):
        results = list(ranked_results)

        if max_context_tokens is None:
            budget = self.max_context_tokens
        else:
            if (
                not isinstance(max_context_tokens, int)
                or max_context_tokens < 0
            ):
                raise ValueError(
                    "max_context_tokens override must be non-negative int"
                )

            budget = min(
                self.max_context_tokens,
                max_context_tokens,
            )

        candidate_citations = self.citation_builder.build(
            results
        )

        accepted = []
        blocks = []
        skipped = []

        index = 0

        while index < len(results):
            source = candidate_citations[index]

            citation = Citation(
                citation_id=(
                    "S"
                    + str(len(accepted) + 1)
                ),
                item_id=source.item_id,
                document_id=source.document_id,
                dataset_id=source.dataset_id,
                text=source.text,
                score=source.score,
                metadata=source.metadata,
                provenance=source.provenance,
            )

            block = self._block(
                citation
            )

            candidate_blocks = (
                blocks + [block]
            )

            candidate_text = "\n\n".join(
                candidate_blocks
            )

            candidate_tokens = len(
                self.tokenizer.encode(
                    candidate_text
                )
            )

            if candidate_tokens <= budget:
                accepted.append(
                    citation
                )
                blocks.append(
                    block
                )
            else:
                skipped.append(
                    results[index]
                    .entry
                    .item_id
                )

            index += 1

        text = "\n\n".join(
            blocks
        )

        actual_count = len(
            self.tokenizer.encode(text)
        )

        return ContextPackage(
            text=text,
            citations=accepted,
            token_count=actual_count,
            skipped_item_ids=skipped,
        )

    def _block(self, citation):
        source_bits = []

        if citation.dataset_id is not None:
            source_bits.append(
                "dataset=" + str(citation.dataset_id)
            )

        if citation.document_id is not None:
            source_bits.append(
                "document=" + str(citation.document_id)
            )

        header = citation.marker()

        if len(source_bits) > 0:
            header += " " + " ".join(
                source_bits
            )

        return (
            header
            + "\n"
            + citation.text
        )
