class RankedResult:
    """
    Final retrieval-ranking record.

    Keeps both raw similarity and reranked score so later RAG stages can inspect
    why an item moved without losing the index's original signal.
    """

    def __init__(
        self,
        entry,
        similarity_score,
        rerank_score=None,
        rank=None,
        reasons=None,
    ):
        if entry is None:
            raise ValueError("entry is required")

        if not isinstance(similarity_score, (int, float)):
            raise TypeError("similarity_score must be numeric")

        if rerank_score is None:
            rerank_score = similarity_score

        if not isinstance(rerank_score, (int, float)):
            raise TypeError("rerank_score must be numeric")

        if rank is not None:
            if not isinstance(rank, int) or rank <= 0:
                raise ValueError("rank must be positive int or None")

        if reasons is None:
            reasons = []

        self.entry = entry
        self.item_id = entry.item_id
        self.similarity_score = float(similarity_score)
        self.rerank_score = float(rerank_score)
        self.rank = rank
        self.reasons = list(reasons)

    def to_dict(self):
        return {
            "item_id": self.item_id,
            "similarity_score": self.similarity_score,
            "rerank_score": self.rerank_score,
            "rank": self.rank,
            "reasons": list(self.reasons),
        }
