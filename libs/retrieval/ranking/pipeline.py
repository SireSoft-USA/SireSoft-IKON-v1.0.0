class RankingPipeline:
    """
    End-to-end retrieval ranking:
      raw index results
        -> duplicate suppression
        -> transparent score reranking
        -> optional MMR diversification
        -> final top-k
    """

    def __init__(
        self,
        reranker=None,
        duplicate_suppressor=None,
        mmr=None,
    ):
        self.reranker = (
            RetrievalReranker()
            if reranker is None
            else reranker
        )

        self.duplicate_suppressor = (
            DuplicateSuppressor()
            if duplicate_suppressor is None
            else duplicate_suppressor
        )

        self.mmr = mmr

        if not hasattr(
            self.reranker,
            "rerank",
        ):
            raise TypeError(
                "reranker must provide rerank()"
            )

        if not hasattr(
            self.duplicate_suppressor,
            "suppress",
        ):
            raise TypeError(
                "duplicate_suppressor must provide suppress()"
            )

        if (
            self.mmr is not None
            and not hasattr(
                self.mmr,
                "select",
            )
        ):
            raise TypeError(
                "mmr must provide select()"
            )

    def rank(
        self,
        search_results,
        top_k=5,
        use_mmr=True,
    ):
        if not isinstance(top_k, int) or top_k <= 0:
            raise ValueError(
                "top_k must be positive int"
            )

        unique = (
            self.duplicate_suppressor.suppress(
                search_results
            )
        )

        reranked = self.reranker.rerank(
            unique,
            top_k=None,
        )

        if (
            use_mmr
            and self.mmr is not None
        ):
            final = self.mmr.select(
                reranked,
                top_k=top_k,
            )
        else:
            final = reranked[
                :top_k
            ]

            rank = 1

            for item in final:
                item.rank = rank
                rank += 1

        return final
