class RetrievalManager:
    """
    End-to-end searchable retrieval core.

    Source documents
      -> exact source-preserving chunks
      -> tokenizer-backed hashed TF-IDF
      -> exact cosine vector index
      -> dedup/rerank/MMR
      -> protocol-safe source/provenance hits
    """

    FNV_OFFSET = 0xCBF29CE484222325
    FNV_PRIME = 0x100000001B3
    MASK = 0xFFFFFFFFFFFFFFFF

    def __init__(
        self,
        tokenizer,
        Document,
        dimension=256,
        min_n=1,
        max_n=2,
        max_chars=1200,
        overlap_chars=150,
        min_chunk_chars=None,
        use_idf=True,
        sublinear_tf=True,
        l2_normalize=True,
        persistence=None,
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

        self.tokenizer = tokenizer
        self.Document = Document

        self.document_store = (
            RetrievalDocumentStore(
                Document
            )
        )

        self.chunker = DocumentChunker(
            max_chars=max_chars,
            overlap_chars=overlap_chars,
            min_chunk_chars=(
                min_chunk_chars
            ),
        )

        self.embedder = (
            HashingTFIDFEmbedder(
                tokenizer=tokenizer,
                dimension=dimension,
                min_n=min_n,
                max_n=max_n,
                use_idf=use_idf,
                sublinear_tf=sublinear_tf,
                l2_normalize=l2_normalize,
            )
        )

        self.index = (
            FlatVectorIndex(
                dimension=dimension,
                metric=CosineSimilarity(),
            )
        )

        self.persistence = (
            RetrievalPersistence()
            if persistence is None
            else persistence
        )

        self._last_chunk_count = 0

    def index_documents(
        self,
        documents,
        mode="replace",
        refit=True,
    ):
        if not isinstance(
            documents,
            (list, tuple),
        ):
            documents = list(
                documents
            )

        if mode == "replace":
            self.document_store.replace_all(
                documents
            )

        elif mode == "upsert":
            self.document_store.upsert_many(
                documents
            )

        else:
            raise ValueError(
                "index mode must be replace or upsert"
            )

        return self.rebuild(
            refit=bool(
                refit
            )
        )

    def remove_document(
        self,
        document_id,
        refit=True,
    ):
        self.document_store.remove(
            document_id
        )

        return self.rebuild(
            refit=bool(
                refit
            )
        )

    def clear(
        self,
    ):
        self.document_store.clear()

        self._reset_embedder(
            dimension=(
                self.embedder
                .dimension
            ),
            min_n=(
                self.embedder
                .min_n
            ),
            max_n=(
                self.embedder
                .max_n
            ),
            use_idf=(
                self.embedder
                .use_idf
            ),
            sublinear_tf=(
                self.embedder
                .sublinear_tf
            ),
            l2_normalize=(
                self.embedder
                .l2_normalize
            ),
        )

        self.index = (
            FlatVectorIndex(
                dimension=(
                    self.embedder
                    .dimension
                ),
                metric=CosineSimilarity(),
            )
        )

        self._last_chunk_count = 0

        return self.status()

    def rebuild(
        self,
        refit=True,
    ):
        chunks = self._all_chunks()

        if len(chunks) == 0:
            self.index = (
                FlatVectorIndex(
                    dimension=(
                        self.embedder
                        .dimension
                    ),
                    metric=CosineSimilarity(),
                )
            )

            self._last_chunk_count = 0

            return self.status()

        if refit:
            self.embedder.fit_chunks(
                chunks
            )

        elif (
            self.embedder.use_idf
            and not self.embedder.idf_model.fitted
        ):
            raise RuntimeError(
                "IDF embedder must be fitted before rebuild(refit=False)"
            )

        new_index = FlatVectorIndex(
            dimension=(
                self.embedder
                .dimension
            ),
            metric=CosineSimilarity(),
        )

        entries = []

        for chunk in chunks:
            embedded = (
                self.embedder
                .embed_chunk(
                    chunk
                )
            )

            metadata = self._copy(
                chunk.metadata
            )

            metadata[
                "chunk_index"
            ] = chunk.chunk_index

            metadata[
                "char_start"
            ] = chunk.char_start

            metadata[
                "char_end"
            ] = chunk.char_end

            metadata[
                "token_start"
            ] = chunk.token_start

            metadata[
                "token_end"
            ] = chunk.token_end

            metadata[
                "embedding_token_count"
            ] = embedded.token_count

            metadata[
                "embedding_nonzero_features"
            ] = (
                embedded
                .nonzero_features
            )

            provenance = self._copy(
                chunk.provenance
            )

            provenance[
                "document_id"
            ] = chunk.document_id

            provenance[
                "chunk_id"
            ] = chunk.chunk_id

            entries.append(
                IndexEntry(
                    item_id=chunk.chunk_id,
                    vector=embedded.vector,
                    text=chunk.text,
                    document_id=(
                        chunk.document_id
                    ),
                    dataset_id=(
                        chunk.dataset_id
                    ),
                    metadata=metadata,
                    provenance=provenance,
                )
            )

        new_index.bulk_add(
            entries
        )

        self.index = new_index
        self._last_chunk_count = len(
            chunks
        )

        return self.status()

    def search(
        self,
        query,
        top_k=5,
        search_k=None,
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
            query,
            str,
        ):
            raise TypeError(
                "query must be str"
            )

        if query.strip() == "":
            raise ValueError(
                "query must not be blank"
            )

        if not isinstance(
            top_k,
            int,
        ) or top_k <= 0:
            raise ValueError(
                "top_k must be positive int"
            )

        if search_k is None:
            search_k = (
                top_k * 4
            )

            if search_k < top_k:
                search_k = top_k

        if (
            not isinstance(
                search_k,
                int,
            )
            or search_k <= 0
        ):
            raise ValueError(
                "search_k must be positive int"
            )

        if search_k < top_k:
            search_k = top_k

        query_embedding = (
            self.embedder
            .embed_text(
                query
            )
        )

        raw = self.index.search(
            query_vector=(
                query_embedding
                .vector
            ),
            top_k=search_k,
            min_score=min_score,
            filters=filters,
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

        pipeline = RankingPipeline(
            reranker=reranker,
            duplicate_suppressor=(
                DuplicateSuppressor()
            ),
            mmr=mmr,
        )

        ranked = pipeline.rank(
            raw,
            top_k=top_k,
            use_mmr=bool(
                use_mmr
            ),
        )

        hits = [
            RetrievalHit(
                item
            )
            for item in ranked
        ]

        return RetrievalSearchResult(
            query=query,
            hits=hits,
            raw_candidate_count=len(
                raw
            ),
            search_k=search_k,
            top_k=top_k,
        )

    def status(
        self,
    ):
        return {
            "documents": (
                self.document_store
                .count()
            ),
            "chunks": (
                self._last_chunk_count
            ),
            "index_entries": (
                self.index
                .count()
            ),
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
            "idf_fitted": (
                self.embedder
                .idf_model
                .fitted
            ),
            "idf_document_count": (
                self.embedder
                .idf_model
                .document_count
            ),
            "max_chars": (
                self.chunker
                .max_chars
            ),
            "overlap_chars": (
                self.chunker
                .overlap_chars
            ),
            "min_chunk_chars": (
                self.chunker
                .min_chunk_chars
            ),
            "tokenizer_signature": (
                self.tokenizer_signature()
            ),
        }

    def save_state(
        self,
        path,
    ):
        return self.persistence.save(
            path,
            self,
        )

    def load_state_file(
        self,
        path,
    ):
        return self.persistence.load(
            path,
            self,
        )

    def export_state(
        self,
    ):
        return {
            "format": (
                "SireLLMRetrievalState"
            ),
            "version": 1,
            "tokenizer_signature": (
                self.tokenizer_signature()
            ),
            "chunking": {
                "max_chars": (
                    self.chunker
                    .max_chars
                ),
                "overlap_chars": (
                    self.chunker
                    .overlap_chars
                ),
                "min_chunk_chars": (
                    self.chunker
                    .min_chunk_chars
                ),
            },
            "embedder": (
                self.embedder
                .state_dict()
            ),
            "index": (
                self.index
                .state_dict()
            ),
            "documents": (
                self.document_store
                .to_state()
            ),
            "last_chunk_count": (
                self._last_chunk_count
            ),
        }

    def load_state(
        self,
        state,
    ):
        if not isinstance(
            state,
            dict,
        ):
            raise TypeError(
                "retrieval state must be dict"
            )

        if state.get(
            "format"
        ) != "SireLLMRetrievalState":
            raise ValueError(
                "invalid retrieval state format"
            )

        if int(
            state.get(
                "version",
                0,
            )
        ) != 1:
            raise ValueError(
                "unsupported retrieval state version"
            )

        if (
            state[
                "tokenizer_signature"
            ]
            != self.tokenizer_signature()
        ):
            raise ValueError(
                "retrieval state tokenizer signature mismatch"
            )

        chunking = state[
            "chunking"
        ]

        embedder_state = state[
            "embedder"
        ]

        dimension = int(
            embedder_state[
                "dimension"
            ]
        )

        staged_embedder = (
            HashingTFIDFEmbedder(
                tokenizer=self.tokenizer,
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
        )

        staged_embedder.load_state_dict(
            embedder_state
        )

        staged_index = (
            FlatVectorIndex(
                dimension=dimension,
                metric=CosineSimilarity(),
            )
        )

        staged_index.load_state_dict(
            state[
                "index"
            ]
        )

        staged_store = (
            RetrievalDocumentStore(
                self.Document
            )
        )

        staged_store.load_state(
            state[
                "documents"
            ]
        )

        staged_chunker = (
            DocumentChunker(
                max_chars=int(
                    chunking[
                        "max_chars"
                    ]
                ),
                overlap_chars=int(
                    chunking[
                        "overlap_chars"
                    ]
                ),
                min_chunk_chars=int(
                    chunking[
                        "min_chunk_chars"
                    ]
                ),
            )
        )

        self.embedder = (
            staged_embedder
        )
        self.index = staged_index
        self.document_store = (
            staged_store
        )
        self.chunker = staged_chunker
        self._last_chunk_count = int(
            state.get(
                "last_chunk_count",
                staged_index.count(),
            )
        )

        return self.status()

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

    def _all_chunks(
        self,
    ):
        chunks = []

        for document in (
            self.document_store
            .documents()
        ):
            chunks.extend(
                self.chunker
                .chunk_document(
                    document
                )
            )

        return chunks

    def _reset_embedder(
        self,
        dimension,
        min_n,
        max_n,
        use_idf,
        sublinear_tf,
        l2_normalize,
    ):
        self.embedder = (
            HashingTFIDFEmbedder(
                tokenizer=self.tokenizer,
                dimension=dimension,
                min_n=min_n,
                max_n=max_n,
                use_idf=use_idf,
                sublinear_tf=sublinear_tf,
                l2_normalize=l2_normalize,
            )
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
