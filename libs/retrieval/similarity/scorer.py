class EmbeddedItem:
    """
    Couples retrieval metadata/item identity with its dense vector.
    """

    def __init__(
        self,
        item_id,
        vector,
        item=None,
        metadata=None,
    ):
        if not isinstance(item_id, str) or item_id == "":
            raise ValueError(
                "item_id must be non-empty str"
            )

        if hasattr(vector, "vector"):
            vector = vector.vector

        if not isinstance(vector, (list, tuple)):
            raise TypeError(
                "vector must be list/tuple or embedding result"
            )

        values = []

        for value in vector:
            if not isinstance(value, (int, float)):
                raise TypeError(
                    "vector elements must be numeric"
                )

            values.append(float(value))

        if metadata is None:
            metadata = {}

        if not isinstance(metadata, dict):
            raise TypeError(
                "metadata must be dict or None"
            )

        self.item_id = item_id
        self.vector = values
        self.item = item
        self.metadata = dict(metadata)


class SimilarityScorer:
    """
    Retrieval-facing scoring facade.

    It embeds a text query with the configured embedder and ranks pre-embedded
    items with BatchSimilarity.
    """

    def __init__(
        self,
        embedder,
        metric=None,
    ):
        if embedder is None or not hasattr(
            embedder,
            "embed_text",
        ):
            raise TypeError(
                "embedder must provide embed_text()"
            )

        self.embedder = embedder
        self.batch = BatchSimilarity(
            metric=metric
        )

    def score_query(
        self,
        query_text,
        embedded_items,
        top_k=None,
        min_score=None,
    ):
        if not isinstance(query_text, str):
            raise TypeError(
                "query_text must be str"
            )

        query_embedding = (
            self.embedder.embed_text(
                query_text
            )
        )

        return self.batch.compare(
            query_vector=query_embedding.vector,
            candidates=embedded_items,
            top_k=top_k,
            min_score=min_score,
        )

    def embed_items(self, items):
        results = []

        for item in items:
            if not hasattr(item, "text"):
                raise TypeError(
                    "item must provide text"
                )

            item_id = self._identity(
                item
            )

            embedding = (
                self.embedder.embed_text(
                    item.text
                )
            )

            metadata = {}

            if hasattr(item, "metadata"):
                for key in item.metadata:
                    metadata[key] = (
                        item.metadata[key]
                    )

            results.append(
                EmbeddedItem(
                    item_id=item_id,
                    vector=embedding.vector,
                    item=item,
                    metadata=metadata,
                )
            )

        return results

    def _identity(self, item):
        for name in (
            "chunk_id",
            "document_id",
            "item_id",
            "id",
        ):
            if hasattr(item, name):
                value = getattr(
                    item,
                    name,
                )

                if value is not None:
                    return str(value)

        raise ValueError(
            "retrieval item has no identifiable ID"
        )
