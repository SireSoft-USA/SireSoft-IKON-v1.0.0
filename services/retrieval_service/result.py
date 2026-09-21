class RetrievalHit:
    """
    User/service-facing retrieval result with source text and provenance.

    Vector payloads are deliberately omitted from the default protocol response.
    """

    def __init__(
        self,
        ranked_result,
    ):
        if ranked_result is None or not hasattr(
            ranked_result,
            "entry",
        ):
            raise TypeError(
                "ranked_result must expose entry"
            )

        entry = ranked_result.entry

        self.item_id = entry.item_id
        self.document_id = entry.document_id
        self.dataset_id = entry.dataset_id
        self.text = entry.text
        self.metadata = self._copy(
            entry.metadata
        )
        self.provenance = self._copy(
            entry.provenance
        )
        self.similarity_score = float(
            ranked_result.similarity_score
        )
        self.rerank_score = float(
            ranked_result.rerank_score
        )
        self.rank = int(
            ranked_result.rank
        )
        self.reasons = list(
            ranked_result.reasons
        )

    def to_dict(
        self,
    ):
        return {
            "item_id": self.item_id,
            "document_id": self.document_id,
            "dataset_id": self.dataset_id,
            "text": self.text,
            "metadata": self._copy(
                self.metadata
            ),
            "provenance": self._copy(
                self.provenance
            ),
            "similarity_score": (
                self.similarity_score
            ),
            "rerank_score": (
                self.rerank_score
            ),
            "rank": self.rank,
            "reasons": list(
                self.reasons
            ),
        }

    def _copy(
        self,
        value,
    ):
        if isinstance(
            value,
            dict,
        ):
            result = {}

            for key in value:
                result[
                    key
                ] = self._copy(
                    value[
                        key
                    ]
                )

            return result

        if isinstance(
            value,
            list,
        ):
            return [
                self._copy(
                    item
                )
                for item in value
            ]

        if isinstance(
            value,
            tuple,
        ):
            return [
                self._copy(
                    item
                )
                for item in value
            ]

        return value


class RetrievalSearchResult:
    def __init__(
        self,
        query,
        hits,
        raw_candidate_count,
        search_k,
        top_k,
    ):
        self.query = query
        self.hits = list(
            hits
        )
        self.raw_candidate_count = int(
            raw_candidate_count
        )
        self.search_k = int(
            search_k
        )
        self.top_k = int(
            top_k
        )

    def to_dict(
        self,
    ):
        return {
            "query": self.query,
            "hits": [
                hit.to_dict()
                for hit in self.hits
            ],
            "count": len(
                self.hits
            ),
            "raw_candidate_count": (
                self.raw_candidate_count
            ),
            "search_k": self.search_k,
            "top_k": self.top_k,
        }
