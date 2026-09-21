class RetrievalBundle:
    def __init__(
        self,
        query_text,
        query_embedding,
        raw_results,
        ranked_results,
    ):
        self.query_text = query_text
        self.query_embedding = query_embedding
        self.raw_results = list(raw_results)
        self.ranked_results = list(ranked_results)

    def to_dict(self):
        return {
            "query_text": self.query_text,
            "raw_count": len(self.raw_results),
            "ranked_count": len(self.ranked_results),
            "ranked": [
                result.to_dict()
                for result in self.ranked_results
            ],
        }


class Retriever:
    """
    Query embedding -> vector index -> retrieval ranking pipeline.
    """

    def __init__(
        self,
        embedder,
        index,
        ranking_pipeline,
    ):
        if embedder is None or not hasattr(embedder, "embed_text"):
            raise TypeError("embedder must provide embed_text()")

        if index is None or not hasattr(index, "search"):
            raise TypeError("index must provide search()")

        if ranking_pipeline is None or not hasattr(
            ranking_pipeline,
            "rank",
        ):
            raise TypeError(
                "ranking_pipeline must provide rank()"
            )

        self.embedder = embedder
        self.index = index
        self.ranking_pipeline = ranking_pipeline

    def retrieve(
        self,
        query_text,
        candidate_k=20,
        top_k=5,
        min_score=None,
        filters=None,
        use_mmr=True,
    ):
        if not isinstance(query_text, str):
            raise TypeError("query_text must be str")

        if query_text.strip() == "":
            raise ValueError("query_text must not be empty")

        if not isinstance(candidate_k, int) or candidate_k <= 0:
            raise ValueError("candidate_k must be positive int")

        if not isinstance(top_k, int) or top_k <= 0:
            raise ValueError("top_k must be positive int")

        if candidate_k < top_k:
            candidate_k = top_k

        query_embedding = self.embedder.embed_text(
            query_text
        )

        raw_results = self.index.search(
            query_vector=query_embedding.vector,
            top_k=candidate_k,
            min_score=min_score,
            filters=filters,
        )

        ranked_results = self.ranking_pipeline.rank(
            raw_results,
            top_k=top_k,
            use_mmr=use_mmr,
        )

        return RetrievalBundle(
            query_text=query_text,
            query_embedding=query_embedding,
            raw_results=raw_results,
            ranked_results=ranked_results,
        )
