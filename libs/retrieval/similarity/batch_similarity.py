class BatchSimilarityResult:
    def __init__(
        self,
        item_id,
        score,
        original_index,
        item=None,
    ):
        self.item_id = item_id
        self.score = float(score)
        self.original_index = int(
            original_index
        )
        self.item = item
        self.rank = None

    def to_dict(self):
        return {
            "item_id": self.item_id,
            "score": self.score,
            "original_index": self.original_index,
            "rank": self.rank,
        }


class BatchSimilarity:
    """
    Scores one query vector against many candidate vectors.

    Stable sorting:
      1. higher score first
      2. lower original index wins ties
    """

    def __init__(self, metric=None):
        if metric is None:
            metric = CosineSimilarity()

        if not hasattr(metric, "score"):
            raise TypeError(
                "metric must provide score(left, right)"
            )

        self.metric = metric

    def compare(
        self,
        query_vector,
        candidates,
        top_k=None,
        min_score=None,
    ):
        if not isinstance(
            candidates,
            (list, tuple),
        ):
            candidates = list(candidates)

        if top_k is not None:
            if not isinstance(top_k, int) or top_k <= 0:
                raise ValueError(
                    "top_k must be positive int or None"
                )

        if min_score is not None and not isinstance(
            min_score,
            (int, float),
        ):
            raise TypeError(
                "min_score must be numeric or None"
            )

        results = []

        index = 0

        while index < len(candidates):
            candidate = candidates[index]

            item_id = self._item_id(
                candidate,
                index,
            )

            vector = self._vector(
                candidate
            )

            score = self.metric.score(
                query_vector,
                vector,
            )

            if (
                min_score is None
                or score >= min_score
            ):
                results.append(
                    BatchSimilarityResult(
                        item_id=item_id,
                        score=score,
                        original_index=index,
                        item=candidate,
                    )
                )

            index += 1

        results.sort(
            key=lambda result: (
                -result.score,
                result.original_index,
            )
        )

        if top_k is not None:
            results = results[:top_k]

        rank = 1

        for result in results:
            result.rank = rank
            rank += 1

        return results

    def _vector(self, candidate):
        if hasattr(candidate, "vector"):
            return candidate.vector

        if isinstance(candidate, dict):
            if "vector" not in candidate:
                raise KeyError(
                    "candidate dict requires vector"
                )

            return candidate["vector"]

        if isinstance(candidate, (list, tuple)):
            return candidate

        raise TypeError(
            "candidate must expose vector, contain vector, or be vector"
        )

    def _item_id(
        self,
        candidate,
        index,
    ):
        for name in (
            "chunk_id",
            "document_id",
            "item_id",
            "id",
        ):
            if hasattr(candidate, name):
                value = getattr(
                    candidate,
                    name,
                )

                if value is not None:
                    return str(value)

        if isinstance(candidate, dict):
            for name in (
                "chunk_id",
                "document_id",
                "item_id",
                "id",
            ):
                if name in candidate:
                    return str(
                        candidate[name]
                    )

        return str(index)
