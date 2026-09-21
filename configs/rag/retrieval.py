class RAGRetrievalConfig:
    def __init__(
        self,
        candidate_k=20,
        top_k=5,
        min_score=None,
        use_mmr=True,
        mmr_lambda=0.75,
        similarity_weight=1.0,
        dataset_boosts=None,
        document_boosts=None,
        metadata_boosts=None,
    ):
        if (
            not isinstance(candidate_k, int)
            or candidate_k <= 0
        ):
            raise ValueError(
                "candidate_k must be positive int"
            )

        if (
            not isinstance(top_k, int)
            or top_k <= 0
        ):
            raise ValueError(
                "top_k must be positive int"
            )

        if min_score is not None and not isinstance(
            min_score,
            (int, float),
        ):
            raise TypeError(
                "min_score must be numeric or None"
            )

        if not isinstance(
            mmr_lambda,
            (int, float),
        ) or (
            mmr_lambda < 0.0
            or mmr_lambda > 1.0
        ):
            raise ValueError(
                "mmr_lambda must satisfy 0 <= value <= 1"
            )

        if not isinstance(
            similarity_weight,
            (int, float),
        ):
            raise TypeError(
                "similarity_weight must be numeric"
            )

        self.candidate_k = candidate_k
        self.top_k = top_k
        self.min_score = (
            None
            if min_score is None
            else float(min_score)
        )
        self.use_mmr = bool(use_mmr)
        self.mmr_lambda = float(
            mmr_lambda
        )
        self.similarity_weight = float(
            similarity_weight
        )
        self.dataset_boosts = self._numeric_map(
            dataset_boosts
        )
        self.document_boosts = self._numeric_map(
            document_boosts
        )
        self.metadata_boosts = self._metadata_map(
            metadata_boosts
        )

    def to_dict(self):
        return {
            "candidate_k": self.candidate_k,
            "top_k": self.top_k,
            "min_score": self.min_score,
            "use_mmr": self.use_mmr,
            "mmr_lambda": self.mmr_lambda,
            "similarity_weight": self.similarity_weight,
            "dataset_boosts": dict(
                self.dataset_boosts
            ),
            "document_boosts": dict(
                self.document_boosts
            ),
            "metadata_boosts": self._copy(
                self.metadata_boosts
            ),
        }

    def _numeric_map(self, value):
        if value is None:
            return {}

        if not isinstance(value, dict):
            raise TypeError(
                "boost map must be dict or None"
            )

        result = {}

        for key in value:
            boost = value[key]

            if not isinstance(
                boost,
                (int, float),
            ):
                raise TypeError(
                    "boost values must be numeric"
                )

            result[key] = float(boost)

        return result

    def _metadata_map(self, value):
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

            if (
                "value" not in rule
                or "boost" not in rule
            ):
                raise ValueError(
                    "metadata boost requires value and boost"
                )

            if not isinstance(
                rule["boost"],
                (int, float),
            ):
                raise TypeError(
                    "metadata boost must be numeric"
                )

            result[key] = {
                "value": self._copy(
                    rule["value"]
                ),
                "boost": float(
                    rule["boost"]
                ),
            }

        return result

    def _copy(self, value):
        if isinstance(value, dict):
            return {
                key: self._copy(value[key])
                for key in value
            }

        if isinstance(value, (list, tuple)):
            return [
                self._copy(item)
                for item in value
            ]

        return value
