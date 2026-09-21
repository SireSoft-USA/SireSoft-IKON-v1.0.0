class RetrievalConfig:
    def __init__(
        self,
        embedding=None,
        chunking=None,
        search=None,
        persistence_path=None,
        default_index_mode="replace",
        default_refit=True,
        metadata=None,
    ):
        if embedding is None:
            embedding = (
                RetrievalEmbeddingConfig()
            )

        if chunking is None:
            chunking = (
                RetrievalChunkingConfig()
            )

        if search is None:
            search = (
                RetrievalSearchConfig()
            )

        if not isinstance(
            embedding,
            RetrievalEmbeddingConfig,
        ):
            raise TypeError(
                "embedding must be RetrievalEmbeddingConfig"
            )

        if not isinstance(
            chunking,
            RetrievalChunkingConfig,
        ):
            raise TypeError(
                "chunking must be RetrievalChunkingConfig"
            )

        if not isinstance(
            search,
            RetrievalSearchConfig,
        ):
            raise TypeError(
                "search must be RetrievalSearchConfig"
            )

        if persistence_path is not None and (
            not isinstance(
                persistence_path,
                str,
            )
            or persistence_path == ""
        ):
            raise ValueError(
                "persistence_path must be non-empty str or None"
            )

        if default_index_mode not in (
            "replace",
            "upsert",
        ):
            raise ValueError(
                "default_index_mode must be replace or upsert"
            )

        if metadata is None:
            metadata = {}

        if not isinstance(
            metadata,
            dict,
        ):
            raise TypeError(
                "metadata must be dict or None"
            )

        self.embedding = embedding
        self.chunking = chunking
        self.search = search
        self.persistence_path = (
            persistence_path
        )
        self.default_index_mode = (
            default_index_mode
        )
        self.default_refit = bool(
            default_refit
        )
        self.metadata = self._copy(
            metadata
        )

    def to_dict(
        self,
    ):
        return {
            "embedding": (
                self.embedding.to_dict()
            ),
            "chunking": (
                self.chunking.to_dict()
            ),
            "search": (
                self.search.to_dict()
            ),
            "persistence_path": (
                self.persistence_path
            ),
            "default_index_mode": (
                self.default_index_mode
            ),
            "default_refit": (
                self.default_refit
            ),
            "metadata": self._copy(
                self.metadata
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
            return {
                key: self._copy(
                    value[
                        key
                    ]
                )
                for key
                in value
            }

        if isinstance(
            value,
            (list, tuple),
        ):
            return [
                self._copy(
                    item
                )
                for item
                in value
            ]

        return value
