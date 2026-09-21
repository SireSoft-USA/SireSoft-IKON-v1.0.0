class TokenChunker:
    """
    Token-window chunker for model/context-size aware retrieval preparation.

    Byte-level BPE may expose token boundaries inside a multi-byte UTF-8
    character. Therefore arbitrary token slices are not always decodable.
    This chunker aligns both window starts and ends to slices accepted by the
    SireLLM tokenizer decoder, preserving all source tokens without exceeding
    max_tokens.
    """

    def __init__(
        self,
        tokenizer,
        max_tokens=256,
        overlap_tokens=32,
    ):
        if tokenizer is None:
            raise ValueError("tokenizer is required")

        if not hasattr(tokenizer, "encode"):
            raise TypeError("tokenizer must provide encode()")

        if not hasattr(tokenizer, "decode"):
            raise TypeError("tokenizer must provide decode()")

        if not isinstance(max_tokens, int) or max_tokens <= 0:
            raise ValueError("max_tokens must be positive int")

        if not isinstance(overlap_tokens, int) or overlap_tokens < 0:
            raise ValueError("overlap_tokens must be non-negative int")

        if overlap_tokens >= max_tokens:
            raise ValueError(
                "overlap_tokens must be smaller than max_tokens"
            )

        self.tokenizer = tokenizer
        self.max_tokens = max_tokens
        self.overlap_tokens = overlap_tokens

    def chunk_document(self, document):
        self._validate_document(document)

        token_ids = self.tokenizer.encode(
            document.text
        )

        if len(token_ids) == 0:
            return []

        chunks = []
        start = 0
        previous_end = 0
        chunk_index = 0

        while start < len(token_ids):
            if chunk_index > 0:
                desired_start = (
                    previous_end
                    - self.overlap_tokens
                )

                if desired_start < 0:
                    desired_start = 0

                start = self._align_start_forward(
                    token_ids,
                    desired_start,
                    previous_end,
                )

                if start >= len(token_ids):
                    break

            hard_end = min(
                start + self.max_tokens,
                len(token_ids),
            )

            end, text = self._aligned_end_and_text(
                token_ids,
                start,
                hard_end,
            )

            if end <= start:
                raise ValueError(
                    "max_tokens is too small to hold a decodable UTF-8 token window"
                )

            metadata = {}

            if hasattr(document, "metadata"):
                for key in document.metadata:
                    metadata[key] = document.metadata[key]

            metadata["chunk_mode"] = "token"
            metadata["source_document_id"] = document.document_id

            provenance = {}

            if hasattr(document, "provenance"):
                for key in document.provenance:
                    provenance[key] = document.provenance[key]

            provenance["chunked_from"] = document.document_id

            chunks.append(
                Chunk(
                    chunk_id=(
                        document.document_id
                        + "::token::"
                        + str(chunk_index)
                    ),
                    document_id=document.document_id,
                    dataset_id=document.dataset_id,
                    text=text,
                    chunk_index=chunk_index,
                    token_start=start,
                    token_end=end,
                    metadata=metadata,
                    provenance=provenance,
                )
            )

            chunk_index += 1
            previous_end = end

            if end >= len(token_ids):
                break

            if self.overlap_tokens == 0:
                start = end

        return chunks

    def _aligned_end_and_text(
        self,
        token_ids,
        start,
        hard_end,
    ):
        end = hard_end

        while end > start:
            try:
                text = self.tokenizer.decode(
                    token_ids[start:end]
                )

                return end, text

            except ValueError:
                end -= 1

        return start, ""

    def _align_start_forward(
        self,
        token_ids,
        desired_start,
        previous_end,
    ):
        candidate = desired_start

        while candidate <= previous_end:
            try:
                self.tokenizer.decode(
                    token_ids[
                        candidate:previous_end
                    ]
                )

                return candidate

            except ValueError:
                candidate += 1

        return previous_end

    def _validate_document(self, document):
        if document is None:
            raise ValueError("document is required")

        for name in ("document_id", "dataset_id", "text"):
            if not hasattr(document, name):
                raise TypeError(
                    "document must provide " + name
                )
