class RetrievalChunkingConfig:
    def __init__(
        self,
        max_chars=1200,
        overlap_chars=150,
        min_chunk_chars=None,
    ):
        if not isinstance(
            max_chars,
            int,
        ) or max_chars <= 0:
            raise ValueError(
                "max_chars must be positive int"
            )

        if not isinstance(
            overlap_chars,
            int,
        ) or overlap_chars < 0:
            raise ValueError(
                "overlap_chars must be non-negative int"
            )

        if overlap_chars >= max_chars:
            raise ValueError(
                "overlap_chars must be smaller than max_chars"
            )

        if min_chunk_chars is None:
            min_chunk_chars = min(
                100,
                max_chars,
            )

        if (
            not isinstance(
                min_chunk_chars,
                int,
            )
            or min_chunk_chars < 0
            or min_chunk_chars
            > max_chars
        ):
            raise ValueError(
                "min_chunk_chars must be int from 0..max_chars"
            )

        self.max_chars = max_chars
        self.overlap_chars = (
            overlap_chars
        )
        self.min_chunk_chars = (
            min_chunk_chars
        )

    def to_dict(
        self,
    ):
        return {
            "max_chars": self.max_chars,
            "overlap_chars": (
                self.overlap_chars
            ),
            "min_chunk_chars": (
                self.min_chunk_chars
            ),
        }
