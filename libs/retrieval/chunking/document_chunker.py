class DocumentChunker:
    """
    Character-window chunker with sentence/paragraph-aware endings.

    Chunk.text is always exactly document.text[char_start:char_end].
    """

    def __init__(
        self,
        max_chars=1200,
        overlap_chars=150,
        min_chunk_chars=None,
        boundary_detector=None,
    ):
        if not isinstance(max_chars, int) or max_chars <= 0:
            raise ValueError("max_chars must be positive int")

        if not isinstance(overlap_chars, int) or overlap_chars < 0:
            raise ValueError("overlap_chars must be non-negative int")

        if overlap_chars >= max_chars:
            raise ValueError(
                "overlap_chars must be smaller than max_chars"
            )

        if min_chunk_chars is None:
            min_chunk_chars = min(100, max_chars)

        if not isinstance(min_chunk_chars, int) or min_chunk_chars < 0:
            raise ValueError(
                "min_chunk_chars must be non-negative int"
            )

        if min_chunk_chars > max_chars:
            raise ValueError(
                "min_chunk_chars cannot exceed max_chars"
            )

        self.max_chars = max_chars
        self.overlap_chars = overlap_chars
        self.min_chunk_chars = min_chunk_chars

        self.boundary_detector = (
            BoundaryDetector()
            if boundary_detector is None
            else boundary_detector
        )

        if not hasattr(self.boundary_detector, "best_end"):
            raise TypeError(
                "boundary_detector must provide best_end()"
            )

    def chunk_document(self, document):
        self._validate_document(document)

        text = document.text

        if len(text) == 0:
            return []

        chunks = []
        start = 0
        chunk_index = 0

        while start < len(text):
            hard_end = start + self.max_chars

            if hard_end >= len(text):
                end = len(text)
            else:
                end = self.boundary_detector.best_end(
                    text=text,
                    start=start,
                    hard_end=hard_end,
                    minimum_end=(
                        start + self.min_chunk_chars
                    ),
                )

            if end <= start:
                end = min(
                    start + self.max_chars,
                    len(text),
                )

            chunks.append(
                Chunk(
                    chunk_id=(
                        document.document_id
                        + "::char::"
                        + str(chunk_index)
                    ),
                    document_id=document.document_id,
                    dataset_id=document.dataset_id,
                    text=text[start:end],
                    chunk_index=chunk_index,
                    char_start=start,
                    char_end=end,
                    metadata=self._chunk_metadata(document),
                    provenance=self._chunk_provenance(document),
                )
            )

            chunk_index += 1

            if end >= len(text):
                break

            next_start = end - self.overlap_chars

            if next_start <= start:
                next_start = start + 1

            start = next_start

        return chunks

    def _chunk_metadata(self, document):
        metadata = {}

        if hasattr(document, "metadata"):
            for key in document.metadata:
                metadata[key] = document.metadata[key]

        metadata["chunk_mode"] = "character"
        metadata["source_document_id"] = document.document_id
        return metadata

    def _chunk_provenance(self, document):
        provenance = {}

        if hasattr(document, "provenance"):
            for key in document.provenance:
                provenance[key] = document.provenance[key]

        provenance["chunked_from"] = document.document_id
        return provenance

    def _validate_document(self, document):
        if document is None:
            raise ValueError("document is required")

        for name in ("document_id", "dataset_id", "text"):
            if not hasattr(document, name):
                raise TypeError(
                    "document must provide " + name
                )

        if not isinstance(document.document_id, str):
            raise TypeError("document_id must be str")

        if not isinstance(document.dataset_id, str):
            raise TypeError("dataset_id must be str")

        if not isinstance(document.text, str):
            raise TypeError("document text must be str")
