class IDFModel:
    """
    Smoothed inverse-document-frequency model over hashed feature buckets.

    idf = log((N + 1) / (df + 1)) + 1
    """

    def __init__(self, dimension, default_idf=1.0):
        if not isinstance(dimension, int) or dimension <= 0:
            raise ValueError("dimension must be positive int")
        if not isinstance(default_idf, (int, float)):
            raise TypeError("default_idf must be numeric")

        self.dimension = dimension
        self.default_idf = float(default_idf)
        self.document_count = 0
        self.document_frequency = [0] * dimension
        self.idf = [self.default_idf] * dimension
        self.fitted = False

    def fit_feature_sets(self, feature_sets):
        self.document_count = 0
        self.document_frequency = [0] * self.dimension

        for features in feature_sets:
            if not isinstance(features, dict):
                raise TypeError("each feature set must be dict")

            seen = {}

            for bucket in features:
                if not isinstance(bucket, int):
                    raise TypeError("feature bucket must be int")
                if bucket < 0 or bucket >= self.dimension:
                    raise IndexError("feature bucket out of range")

                seen[bucket] = True

            for bucket in seen:
                self.document_frequency[bucket] += 1

            self.document_count += 1

        if self.document_count == 0:
            raise ValueError("IDF fitting requires at least one document")

        self.idf = []
        bucket = 0

        while bucket < self.dimension:
            df = self.document_frequency[bucket]

            self.idf.append(
                log(
                    (self.document_count + 1.0)
                    / (df + 1.0)
                )
                + 1.0
            )

            bucket += 1

        self.fitted = True
        return self

    def weight(self, bucket):
        if not isinstance(bucket, int):
            raise TypeError("bucket must be int")
        if bucket < 0 or bucket >= self.dimension:
            raise IndexError("feature bucket out of range")

        if not self.fitted:
            return self.default_idf

        return self.idf[bucket]

    def state_dict(self):
        return {
            "dimension": self.dimension,
            "default_idf": self.default_idf,
            "document_count": self.document_count,
            "document_frequency": list(self.document_frequency),
            "idf": list(self.idf),
            "fitted": self.fitted,
        }

    def load_state_dict(self, state):
        if not isinstance(state, dict):
            raise TypeError("state must be dict")

        if int(state["dimension"]) != self.dimension:
            raise ValueError("IDF dimension mismatch")

        frequencies = list(state["document_frequency"])
        idf_values = list(state["idf"])

        if len(frequencies) != self.dimension:
            raise ValueError("document_frequency size mismatch")
        if len(idf_values) != self.dimension:
            raise ValueError("idf size mismatch")

        self.default_idf = float(
            state.get("default_idf", self.default_idf)
        )
        self.document_count = int(
            state.get("document_count", 0)
        )
        self.document_frequency = [
            int(value) for value in frequencies
        ]
        self.idf = [
            float(value) for value in idf_values
        ]
        self.fitted = bool(
            state.get("fitted", False)
        )

        return self
