class RAGRetrievalBridge:
    """
    Connects retrieval_service's live embedder/index to libs/rag RetrievalBundle.

    Ranking remains request-configurable while using the same underlying vector
    space and index owned by RetrievalManager.
    """

    def __init__(
        self,
        retrieval_manager,
    ):
        if retrieval_manager is None:
            raise ValueError(
                "retrieval_manager is required"
            )

        if not hasattr(
            retrieval_manager,
            "embedder",
        ):
            raise TypeError(
                "retrieval_manager must expose embedder"
            )

        if not hasattr(
            retrieval_manager,
            "index",
        ):
            raise TypeError(
                "retrieval_manager must expose index"
            )

        self.retrieval_manager = (
            retrieval_manager
        )

    def retrieve(
        self,
        query_text,
        candidate_k=20,
        top_k=5,
        min_score=None,
        filters=None,
        use_mmr=True,
        mmr_lambda=0.75,
        similarity_weight=1.0,
        dataset_boosts=None,
        document_boosts=None,
        metadata_boosts=None,
    ):
        if not isinstance(
            query_text,
            str,
        ):
            raise TypeError(
                "query_text must be str"
            )

        if query_text.strip() == "":
            raise ValueError(
                "query_text must not be empty"
            )

        if (
            not isinstance(
                candidate_k,
                int,
            )
            or candidate_k <= 0
        ):
            raise ValueError(
                "candidate_k must be positive int"
            )

        if (
            not isinstance(
                top_k,
                int,
            )
            or top_k <= 0
        ):
            raise ValueError(
                "top_k must be positive int"
            )

        if candidate_k < top_k:
            candidate_k = top_k

        query_embedding = (
            self.retrieval_manager
            .embedder
            .embed_text(
                query_text
            )
        )

        raw_results = (
            self.retrieval_manager
            .index
            .search(
                query_vector=(
                    query_embedding
                    .vector
                ),
                top_k=candidate_k,
                min_score=min_score,
                filters=filters,
            )
        )

        reranker = RetrievalReranker(
            similarity_weight=(
                similarity_weight
            ),
            dataset_boosts=(
                dataset_boosts
            ),
            document_boosts=(
                document_boosts
            ),
            metadata_boosts=(
                metadata_boosts
            ),
        )

        mmr = None

        if use_mmr:
            mmr = MaximalMarginalRelevance(
                lambda_relevance=(
                    mmr_lambda
                ),
                similarity_metric=(
                    CosineSimilarity()
                ),
            )

        ranking_pipeline = (
            RankingPipeline(
                reranker=reranker,
                duplicate_suppressor=(
                    DuplicateSuppressor()
                ),
                mmr=mmr,
            )
        )

        ranked_results = (
            ranking_pipeline
            .rank(
                raw_results,
                top_k=top_k,
                use_mmr=bool(
                    use_mmr
                ),
            )
        )

        return RetrievalBundle(
            query_text=query_text,
            query_embedding=(
                query_embedding
            ),
            raw_results=raw_results,
            ranked_results=(
                ranked_results
            ),
        )
