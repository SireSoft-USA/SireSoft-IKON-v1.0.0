class RetrievalConfigCodec:
    def __init__(
        self,
        parser=None,
    ):
        self.parser = (
            JSONParser()
            if parser is None
            else parser
        )

    def decode_text(
        self,
        text,
    ):
        if not isinstance(
            text,
            str,
        ):
            raise TypeError(
                "retrieval config text must be str"
            )

        return self.from_dict(
            self.parser.parse(
                text
            )
        )

    def from_dict(
        self,
        value,
    ):
        if not isinstance(
            value,
            dict,
        ):
            raise ValueError(
                "retrieval config root must be object"
            )

        embedding = value.get(
            "embedding",
            {},
        )

        chunking = value.get(
            "chunking",
            {},
        )

        search = value.get(
            "search",
            {},
        )

        for name, section in (
            (
                "embedding",
                embedding,
            ),
            (
                "chunking",
                chunking,
            ),
            (
                "search",
                search,
            ),
        ):
            if not isinstance(
                section,
                dict,
            ):
                raise ValueError(
                    name
                    + " section must be object"
                )

        return RetrievalConfig(
            embedding=(
                RetrievalEmbeddingConfig(
                    dimension=embedding.get(
                        "dimension",
                        256,
                    ),
                    min_n=embedding.get(
                        "min_n",
                        1,
                    ),
                    max_n=embedding.get(
                        "max_n",
                        2,
                    ),
                    use_idf=embedding.get(
                        "use_idf",
                        True,
                    ),
                    sublinear_tf=embedding.get(
                        "sublinear_tf",
                        True,
                    ),
                    l2_normalize=embedding.get(
                        "l2_normalize",
                        True,
                    ),
                )
            ),
            chunking=(
                RetrievalChunkingConfig(
                    max_chars=chunking.get(
                        "max_chars",
                        1200,
                    ),
                    overlap_chars=chunking.get(
                        "overlap_chars",
                        150,
                    ),
                    min_chunk_chars=(
                        chunking.get(
                            "min_chunk_chars"
                        )
                    ),
                )
            ),
            search=(
                RetrievalSearchConfig(
                    top_k=search.get(
                        "top_k",
                        5,
                    ),
                    search_k=search.get(
                        "search_k"
                    ),
                    min_score=search.get(
                        "min_score"
                    ),
                    use_mmr=search.get(
                        "use_mmr",
                        True,
                    ),
                    mmr_lambda=search.get(
                        "mmr_lambda",
                        0.75,
                    ),
                    similarity_weight=(
                        search.get(
                            "similarity_weight",
                            1.0,
                        )
                    ),
                    dataset_boosts=(
                        search.get(
                            "dataset_boosts"
                        )
                    ),
                    document_boosts=(
                        search.get(
                            "document_boosts"
                        )
                    ),
                    metadata_boosts=(
                        search.get(
                            "metadata_boosts"
                        )
                    ),
                )
            ),
            persistence_path=value.get(
                "persistence_path"
            ),
            default_index_mode=value.get(
                "default_index_mode",
                "replace",
            ),
            default_refit=value.get(
                "default_refit",
                True,
            ),
            metadata=value.get(
                "metadata",
                {},
            ),
        )
