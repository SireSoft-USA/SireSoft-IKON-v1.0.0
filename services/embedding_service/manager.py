class EmbeddingManager:
    """
    Owns SireLLM's deterministic tokenizer-backed hashed TF-IDF embedder.

    This is a lexical retrieval representation, not a pretrained semantic model.
    """

    FNV_OFFSET = 0xCBF29CE484222325
    FNV_PRIME = 0x100000001B3
    MASK = 0xFFFFFFFFFFFFFFFF

    def __init__(
        self,
        tokenizer,
        dimension=256,
        min_n=1,
        max_n=2,
        use_idf=True,
        sublinear_tf=True,
        l2_normalize=True,
        state_codec=None,
    ):
        self._validate_tokenizer(
            tokenizer
        )

        self.tokenizer = tokenizer

        self.state_codec = (
            EmbeddingStateCodec()
            if state_codec is None
            else state_codec
        )

        self.embedder = None
        self.configure(
            dimension=dimension,
            min_n=min_n,
            max_n=max_n,
            use_idf=use_idf,
            sublinear_tf=sublinear_tf,
            l2_normalize=l2_normalize,
        )

    def configure(
        self,
        dimension=256,
        min_n=1,
        max_n=2,
        use_idf=True,
        sublinear_tf=True,
        l2_normalize=True,
    ):
        if (
            not isinstance(
                dimension,
                int,
            )
            or dimension <= 0
        ):
            raise ValueError(
                "dimension must be positive int"
            )

        if (
            not isinstance(
                min_n,
                int,
            )
            or min_n <= 0
        ):
            raise ValueError(
                "min_n must be positive int"
            )

        if (
            not isinstance(
                max_n,
                int,
            )
            or max_n < min_n
        ):
            raise ValueError(
                "max_n must be int >= min_n"
            )

        self.embedder = (
            HashingTFIDFEmbedder(
                tokenizer=self.tokenizer,
                dimension=dimension,
                min_n=min_n,
                max_n=max_n,
                use_idf=bool(
                    use_idf
                ),
                sublinear_tf=bool(
                    sublinear_tf
                ),
                l2_normalize=bool(
                    l2_normalize
                ),
            )
        )

        return self.info()

    def fit(
        self,
        texts,
    ):
        if not isinstance(
            texts,
            (list, tuple),
        ):
            texts = list(
                texts
            )

        if len(texts) == 0:
            raise ValueError(
                "embedding fit requires at least one text"
            )

        self.embedder.fit(
            texts
        )

        return self.info()

    def embed_text(
        self,
        text,
    ):
        return (
            self.embedder
            .embed_text(
                text
            )
        )

    def embed_tokens(
        self,
        token_ids,
    ):
        return (
            self.embedder
            .embed_tokens(
                token_ids
            )
        )

    def embed_many(
        self,
        texts,
    ):
        if not isinstance(
            texts,
            (list, tuple),
        ):
            texts = list(
                texts
            )

        return (
            self.embedder
            .embed_many(
                texts
            )
        )

    def export_state(
        self,
    ):
        return EmbeddingArtifact(
            tokenizer_signature=(
                self.tokenizer_signature()
            ),
            embedder_state=(
                self.embedder
                .state_dict()
            ),
        ).to_dict()

    def load_state(
        self,
        state,
        expected_dimension=None,
    ):
        artifact = (
            EmbeddingArtifact
            .from_dict(
                state
            )
        )

        current_signature = (
            self.tokenizer_signature()
        )

        if (
            artifact.tokenizer_signature
            != current_signature
        ):
            raise ValueError(
                "embedding state tokenizer signature mismatch"
            )

        embedder_state = (
            artifact.embedder_state
        )

        dimension = int(
            embedder_state[
                "dimension"
            ]
        )

        if (
            expected_dimension
            is not None
        ):
            if (
                not isinstance(
                    expected_dimension,
                    int,
                )
                or expected_dimension <= 0
            ):
                raise ValueError(
                    "expected_dimension must be positive int or None"
                )

            if (
                dimension
                != expected_dimension
            ):
                raise ValueError(
                    "embedding state dimension does not match expected_dimension"
                )

        self.configure(
            dimension=dimension,
            min_n=int(
                embedder_state[
                    "min_n"
                ]
            ),
            max_n=int(
                embedder_state[
                    "max_n"
                ]
            ),
            use_idf=bool(
                embedder_state[
                    "use_idf"
                ]
            ),
            sublinear_tf=bool(
                embedder_state[
                    "sublinear_tf"
                ]
            ),
            l2_normalize=bool(
                embedder_state[
                    "l2_normalize"
                ]
            ),
        )

        self.embedder.load_state_dict(
            embedder_state
        )

        return self.info()

    def save_state_file(
        self,
        path,
    ):
        artifact = (
            EmbeddingArtifact
            .from_dict(
                self.export_state()
            )
        )

        return self.state_codec.save(
            path,
            artifact,
        )

    def load_state_file(
        self,
        path,
        expected_dimension=None,
    ):
        artifact = (
            self.state_codec
            .load(
                path
            )
        )

        return self.load_state(
            artifact.to_dict(),
            expected_dimension=(
                expected_dimension
            ),
        )

    def info(
        self,
    ):
        idf = (
            self.embedder
            .idf_model
        )

        return {
            "type": "HashingTFIDFEmbedder",
            "dimension": (
                self.embedder
                .dimension
            ),
            "min_n": (
                self.embedder
                .min_n
            ),
            "max_n": (
                self.embedder
                .max_n
            ),
            "use_idf": (
                self.embedder
                .use_idf
            ),
            "sublinear_tf": (
                self.embedder
                .sublinear_tf
            ),
            "l2_normalize": (
                self.embedder
                .l2_normalize
            ),
            "idf_fitted": (
                idf.fitted
            ),
            "idf_document_count": (
                idf.document_count
            ),
            "tokenizer_signature": (
                self.tokenizer_signature()
            ),
            "representation": (
                "lexical_hashed_tfidf"
            ),
        }

    def tokenizer_signature(
        self,
    ):
        value = self.FNV_OFFSET

        model = self.tokenizer.model

        value = self._hash_int(
            value,
            model.vocabulary.size(),
        )

        for left, right, new_id in model.merges:
            value = self._hash_int(
                value,
                left,
            )

            value = self._hash_int(
                value,
                right,
            )

            value = self._hash_int(
                value,
                new_id,
            )

        for token in (
            self.tokenizer
            .special_tokens
            .all()
        ):
            for byte_value in token.encode(
                "utf-8"
            ):
                value ^= byte_value
                value = (
                    value
                    * self.FNV_PRIME
                ) & self.MASK

            value ^= 0xFF
            value = (
                value
                * self.FNV_PRIME
            ) & self.MASK

        return self._hex64(
            value
        )

    def _hash_int(
        self,
        value,
        number,
    ):
        number = int(
            number
        ) & self.MASK

        shift = 0

        while shift < 64:
            byte_value = (
                number
                >> shift
            ) & 0xFF

            value ^= byte_value
            value = (
                value
                * self.FNV_PRIME
            ) & self.MASK

            shift += 8

        return value

    def _hex64(
        self,
        value,
    ):
        digits = (
            "0123456789abcdef"
        )

        result = ""
        index = 0

        while index < 16:
            shift = (
                60
                - index * 4
            )

            result += digits[
                (
                    value
                    >> shift
                )
                & 0xF
            ]

            index += 1

        return result

    def _validate_tokenizer(
        self,
        tokenizer,
    ):
        if tokenizer is None or not hasattr(
            tokenizer,
            "encode",
        ):
            raise TypeError(
                "tokenizer must provide encode()"
            )

        if not hasattr(
            tokenizer,
            "model",
        ):
            raise TypeError(
                "tokenizer must expose model"
            )

        if not hasattr(
            tokenizer,
            "special_tokens",
        ):
            raise TypeError(
                "tokenizer must expose special_tokens"
            )
