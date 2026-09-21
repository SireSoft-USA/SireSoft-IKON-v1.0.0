class EmbeddingResult:
    def __init__(self, vector, token_count, nonzero_features):
        self.vector = list(vector)
        self.token_count = int(token_count)
        self.nonzero_features = int(nonzero_features)

    def dimension(self):
        return len(self.vector)

    def to_dict(self):
        return {
            "vector": list(self.vector),
            "token_count": self.token_count,
            "nonzero_features": self.nonzero_features,
        }


class HashingTFIDFEmbedder:
    """
    Deterministic zero-API retrieval embedding.

    text -> SireLLM byte-BPE -> hashed token n-grams -> TF-IDF -> L2 vector

    This is a lexical retrieval representation. It does not pretend to be a
    pretrained semantic embedding model.
    """

    def __init__(
        self,
        tokenizer,
        dimension=256,
        min_n=1,
        max_n=2,
        use_idf=True,
        sublinear_tf=True,
        l2_normalize=True,
    ):
        if tokenizer is None:
            raise ValueError("tokenizer is required")
        if not hasattr(tokenizer, "encode"):
            raise TypeError("tokenizer must provide encode()")

        self.tokenizer = tokenizer
        self.dimension = dimension
        self.min_n = min_n
        self.max_n = max_n
        self.use_idf = bool(use_idf)
        self.sublinear_tf = bool(sublinear_tf)
        self.l2_normalize = bool(l2_normalize)

        self.features = HashedNGramFeatures(
            dimension=dimension,
            min_n=min_n,
            max_n=max_n,
            use_sign_hash=True,
        )

        self.idf_model = IDFModel(
            dimension
        )

    def fit(self, texts):
        if not isinstance(texts, (list, tuple)):
            texts = list(texts)

        feature_sets = []

        for text in texts:
            if not isinstance(text, str):
                raise TypeError("fit texts must be strings")

            token_ids = self.tokenizer.encode(text)

            feature_sets.append(
                self.features.presence(token_ids)
            )

        self.idf_model.fit_feature_sets(
            feature_sets
        )

        return self

    def fit_chunks(self, chunks):
        texts = []

        for chunk in chunks:
            if not hasattr(chunk, "text"):
                raise TypeError("chunk must provide text")
            texts.append(chunk.text)

        return self.fit(texts)

    def embed_text(self, text):
        if not isinstance(text, str):
            raise TypeError("text must be str")

        return self.embed_tokens(
            self.tokenizer.encode(text)
        )

    def embed_tokens(self, token_ids):
        counts = self.features.extract(token_ids)

        vector = [
            0.0
            for _ in range(self.dimension)
        ]

        for bucket in counts:
            raw_count = counts[bucket]

            if raw_count == 0.0:
                continue

            if raw_count < 0.0:
                sign = -1.0
                magnitude = -raw_count
            else:
                sign = 1.0
                magnitude = raw_count

            if self.sublinear_tf:
                tf = 1.0 + log(magnitude)
            else:
                tf = magnitude

            weight = sign * tf

            if self.use_idf:
                weight *= self.idf_model.weight(bucket)

            vector[bucket] = weight

        if self.l2_normalize:
            vector = self._normalize(vector)

        nonzero = 0

        for value in vector:
            if value != 0.0:
                nonzero += 1

        return EmbeddingResult(
            vector,
            len(token_ids),
            nonzero,
        )

    def embed_chunk(self, chunk):
        if not hasattr(chunk, "text"):
            raise TypeError("chunk must provide text")

        return self.embed_text(chunk.text)

    def embed_many(self, texts):
        results = []

        for text in texts:
            results.append(
                self.embed_text(text)
            )

        return results

    def _normalize(self, vector):
        total = 0.0

        for value in vector:
            total += value * value

        if total == 0.0:
            return list(vector)

        magnitude = sqrt(total)

        return [
            value / magnitude
            for value in vector
        ]

    def state_dict(self):
        return {
            "type": "HashingTFIDFEmbedder",
            "dimension": self.dimension,
            "min_n": self.min_n,
            "max_n": self.max_n,
            "use_idf": self.use_idf,
            "sublinear_tf": self.sublinear_tf,
            "l2_normalize": self.l2_normalize,
            "idf_model": self.idf_model.state_dict(),
        }

    def load_state_dict(self, state):
        if not isinstance(state, dict):
            raise TypeError("state must be dict")

        if state.get("type") not in (
            None,
            "HashingTFIDFEmbedder",
        ):
            raise ValueError("embedder state type mismatch")

        if int(state["dimension"]) != self.dimension:
            raise ValueError("embedder dimension mismatch")
        if int(state["min_n"]) != self.min_n:
            raise ValueError("embedder min_n mismatch")
        if int(state["max_n"]) != self.max_n:
            raise ValueError("embedder max_n mismatch")

        self.use_idf = bool(state["use_idf"])
        self.sublinear_tf = bool(state["sublinear_tf"])
        self.l2_normalize = bool(state["l2_normalize"])

        self.idf_model.load_state_dict(
            state["idf_model"]
        )

        return self
