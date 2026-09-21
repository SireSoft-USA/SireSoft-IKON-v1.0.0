class RetrievalReranker:
    """
    Deterministic rule-based reranker layered on top of vector similarity.

    Base score:
        rerank = similarity * similarity_weight

    Optional transparent boosts:
      - dataset boost
      - metadata equality boost
      - document boost

    Boosts are additive and fully configurable. Nothing is hard-coded to
    SireSoft except what the caller explicitly provides.
    """

    def __init__(
        self,
        similarity_weight=1.0,
        dataset_boosts=None,
        document_boosts=None,
        metadata_boosts=None,
    ):
        if not isinstance(similarity_weight, (int, float)):
            raise TypeError(
                "similarity_weight must be numeric"
            )

        self.similarity_weight = float(
            similarity_weight
        )

        self.dataset_boosts = self._copy_numeric_map(
            dataset_boosts
        )

        self.document_boosts = self._copy_numeric_map(
            document_boosts
        )

        self.metadata_boosts = self._copy_metadata_boosts(
            metadata_boosts
        )

    def rerank(
        self,
        search_results,
        top_k=None,
    ):
        if not isinstance(search_results, (list, tuple)):
            search_results = list(search_results)

        if top_k is not None:
            if not isinstance(top_k, int) or top_k <= 0:
                raise ValueError(
                    "top_k must be positive int or None"
                )

        ranked = []
        original_index = 0

        for result in search_results:
            if not hasattr(result, "entry"):
                raise TypeError(
                    "search result must expose entry"
                )

            if not hasattr(result, "score"):
                raise TypeError(
                    "search result must expose score"
                )

            entry = result.entry
            reasons = []

            score = (
                float(result.score)
                * self.similarity_weight
            )

            if self.similarity_weight != 1.0:
                reasons.append(
                    "similarity_weight="
                    + str(self.similarity_weight)
                )

            if entry.dataset_id in self.dataset_boosts:
                boost = self.dataset_boosts[
                    entry.dataset_id
                ]

                score += boost

                reasons.append(
                    "dataset_boost="
                    + str(boost)
                )

            if entry.document_id in self.document_boosts:
                boost = self.document_boosts[
                    entry.document_id
                ]

                score += boost

                reasons.append(
                    "document_boost="
                    + str(boost)
                )

            metadata = getattr(
                entry,
                "metadata",
                {},
            )

            if isinstance(metadata, dict):
                for key in self.metadata_boosts:
                    rule = self.metadata_boosts[
                        key
                    ]

                    expected = rule[
                        "value"
                    ]

                    boost = rule[
                        "boost"
                    ]

                    if (
                        key in metadata
                        and metadata[key] == expected
                    ):
                        score += boost

                        reasons.append(
                            "metadata:"
                            + str(key)
                            + "="
                            + str(boost)
                        )

            ranked.append(
                (
                    score,
                    original_index,
                    RankedResult(
                        entry=entry,
                        similarity_score=result.score,
                        rerank_score=score,
                        reasons=reasons,
                    ),
                )
            )

            original_index += 1

        ranked.sort(
            key=lambda row: (
                -row[0],
                row[1],
            )
        )

        if top_k is not None:
            ranked = ranked[:top_k]

        results = []
        rank = 1

        for score, original_index, item in ranked:
            item.rank = rank
            results.append(item)
            rank += 1

        return results

    def _copy_numeric_map(self, value):
        if value is None:
            return {}

        if not isinstance(value, dict):
            raise TypeError(
                "boost map must be dict or None"
            )

        result = {}

        for key in value:
            boost = value[key]

            if not isinstance(boost, (int, float)):
                raise TypeError(
                    "boost values must be numeric"
                )

            result[key] = float(boost)

        return result

    def _copy_metadata_boosts(
        self,
        value,
    ):
        if value is None:
            return {}

        if not isinstance(value, dict):
            raise TypeError(
                "metadata_boosts must be dict or None"
            )

        result = {}

        for key in value:
            rule = value[key]

            if not isinstance(rule, dict):
                raise TypeError(
                    "metadata boost rule must be dict"
                )

            if "value" not in rule or "boost" not in rule:
                raise ValueError(
                    "metadata boost rule requires value and boost"
                )

            if not isinstance(
                rule["boost"],
                (int, float),
            ):
                raise TypeError(
                    "metadata boost must be numeric"
                )

            result[key] = {
                "value": rule["value"],
                "boost": float(
                    rule["boost"]
                ),
            }

        return result
