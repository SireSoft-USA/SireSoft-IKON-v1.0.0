class MaximalMarginalRelevance:
    """
    Diversity-aware reranking with Maximum Marginal Relevance.

    selection_score =
        lambda * relevance
        - (1-lambda) * max_similarity_to_selected

    Candidate relevance comes from rerank_score when present, otherwise
    similarity_score/score. Pairwise candidate similarity uses cosine vectors.
    """

    def __init__(
        self,
        lambda_relevance=0.75,
        similarity_metric=None,
    ):
        if not isinstance(
            lambda_relevance,
            (int, float),
        ):
            raise TypeError(
                "lambda_relevance must be numeric"
            )

        if (
            lambda_relevance < 0.0
            or lambda_relevance > 1.0
        ):
            raise ValueError(
                "lambda_relevance must satisfy 0 <= value <= 1"
            )

        self.lambda_relevance = float(
            lambda_relevance
        )

        if similarity_metric is None:
            similarity_metric = CosineSimilarity()

        if not hasattr(
            similarity_metric,
            "score",
        ):
            raise TypeError(
                "similarity_metric must provide score()"
            )

        self.similarity_metric = (
            similarity_metric
        )

    def select(
        self,
        candidates,
        top_k,
    ):
        if not isinstance(top_k, int) or top_k <= 0:
            raise ValueError(
                "top_k must be positive int"
            )

        remaining = list(candidates)
        selected = []

        while (
            len(remaining) > 0
            and len(selected) < top_k
        ):
            best_index = None
            best_score = None

            index = 0

            while index < len(remaining):
                candidate = remaining[
                    index
                ]

                relevance = self._relevance(
                    candidate
                )

                redundancy = 0.0

                if len(selected) > 0:
                    candidate_vector = (
                        self._vector(
                            candidate
                        )
                    )

                    for chosen in selected:
                        pair_score = (
                            self.similarity_metric.score(
                                candidate_vector,
                                self._vector(
                                    chosen
                                ),
                            )
                        )

                        if pair_score > redundancy:
                            redundancy = pair_score

                selection_score = (
                    self.lambda_relevance
                    * relevance
                    - (
                        1.0
                        - self.lambda_relevance
                    )
                    * redundancy
                )

                if (
                    best_score is None
                    or selection_score
                    > best_score
                ):
                    best_score = selection_score
                    best_index = index

                index += 1

            selected.append(
                remaining.pop(
                    best_index
                )
            )

        rank = 1

        for item in selected:
            if hasattr(item, "rank"):
                item.rank = rank

            if hasattr(item, "reasons"):
                item.reasons.append(
                    "mmr_rank="
                    + str(rank)
                )

            rank += 1

        return selected

    def _relevance(self, candidate):
        if hasattr(
            candidate,
            "rerank_score",
        ):
            return float(
                candidate.rerank_score
            )

        if hasattr(
            candidate,
            "similarity_score",
        ):
            return float(
                candidate.similarity_score
            )

        if hasattr(
            candidate,
            "score",
        ):
            return float(
                candidate.score
            )

        raise TypeError(
            "candidate has no relevance score"
        )

    def _vector(self, candidate):
        if hasattr(
            candidate,
            "entry",
        ):
            entry = candidate.entry
        else:
            entry = candidate

        if not hasattr(
            entry,
            "vector",
        ):
            raise TypeError(
                "candidate entry must provide vector"
            )

        return entry.vector
