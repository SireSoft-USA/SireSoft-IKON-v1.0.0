class FlatVectorIndex:
    """
    Exact in-memory vector index.

    Search is exhaustive O(N) by design. This is the correctness-first baseline
    for SireLLM before approximate indexing is introduced later.

    Features:
      - strict fixed dimension
      - add / bulk add / upsert / remove
      - stable insertion order
      - cosine (or compatible) metric
      - top-k / threshold search
      - dataset/document/metadata filters
      - chunk/EmbeddedItem ingestion helpers
    """

    def __init__(
        self,
        dimension,
        metric=None,
    ):
        if not isinstance(dimension, int) or dimension <= 0:
            raise ValueError("dimension must be positive int")

        if metric is None:
            metric = CosineSimilarity()

        if not hasattr(metric, "score"):
            raise TypeError(
                "metric must provide score(left, right)"
            )

        self.dimension = dimension
        self.metric = metric
        self._entries = {}
        self._order = []

    def __len__(self):
        return len(self._order)

    def count(self):
        return len(self._order)

    def ids(self):
        return list(self._order)

    def contains(self, item_id):
        return item_id in self._entries

    def get(self, item_id):
        if not isinstance(item_id, str):
            raise TypeError("item_id must be str")

        if item_id not in self._entries:
            raise KeyError(
                "index item not found: " + item_id
            )

        return self._entries[item_id]

    def add(self, entry):
        self._validate_entry(entry)

        if entry.item_id in self._entries:
            raise ValueError(
                "duplicate index item_id: "
                + entry.item_id
            )

        self._entries[entry.item_id] = entry
        self._order.append(entry.item_id)
        return self

    def bulk_add(self, entries):
        entries = list(entries)

        staged_ids = {}

        # Validate every entry before mutating index: transactional semantics.
        for entry in entries:
            self._validate_entry(entry)

            if entry.item_id in self._entries:
                raise ValueError(
                    "duplicate existing item_id: "
                    + entry.item_id
                )

            if entry.item_id in staged_ids:
                raise ValueError(
                    "duplicate item_id inside batch: "
                    + entry.item_id
                )

            staged_ids[entry.item_id] = True

        for entry in entries:
            self._entries[entry.item_id] = entry
            self._order.append(entry.item_id)

        return self

    def upsert(self, entry):
        self._validate_entry(entry)

        if entry.item_id not in self._entries:
            self._order.append(
                entry.item_id
            )

        self._entries[entry.item_id] = entry
        return self

    def remove(self, item_id):
        if not isinstance(item_id, str):
            raise TypeError("item_id must be str")

        if item_id not in self._entries:
            raise KeyError(
                "index item not found: " + item_id
            )

        entry = self._entries.pop(
            item_id
        )

        new_order = []

        for existing_id in self._order:
            if existing_id != item_id:
                new_order.append(
                    existing_id
                )

        self._order = new_order
        return entry

    def clear(self):
        self._entries = {}
        self._order = []
        return self

    def add_embedded(self, embedded_item):
        if embedded_item is None:
            raise ValueError(
                "embedded_item is required"
            )

        if not hasattr(
            embedded_item,
            "item_id",
        ):
            raise TypeError(
                "embedded_item must provide item_id"
            )

        if not hasattr(
            embedded_item,
            "vector",
        ):
            raise TypeError(
                "embedded_item must provide vector"
            )

        original = getattr(
            embedded_item,
            "item",
            None,
        )

        text = ""
        document_id = None
        dataset_id = None
        metadata = {}
        provenance = {}

        if original is not None:
            text = getattr(
                original,
                "text",
                "",
            )

            document_id = getattr(
                original,
                "document_id",
                None,
            )

            dataset_id = getattr(
                original,
                "dataset_id",
                None,
            )

            original_metadata = getattr(
                original,
                "metadata",
                {},
            )

            if isinstance(
                original_metadata,
                dict,
            ):
                metadata = dict(
                    original_metadata
                )

            original_provenance = getattr(
                original,
                "provenance",
                {},
            )

            if isinstance(
                original_provenance,
                dict,
            ):
                provenance = dict(
                    original_provenance
                )

        embedded_metadata = getattr(
            embedded_item,
            "metadata",
            {},
        )

        if isinstance(
            embedded_metadata,
            dict,
        ):
            for key in embedded_metadata:
                metadata[key] = (
                    embedded_metadata[key]
                )

        entry = IndexEntry(
            item_id=str(
                embedded_item.item_id
            ),
            vector=embedded_item.vector,
            text=text,
            document_id=document_id,
            dataset_id=dataset_id,
            metadata=metadata,
            provenance=provenance,
        )

        self.add(entry)
        return entry

    def search(
        self,
        query_vector,
        top_k=5,
        min_score=None,
        filters=None,
    ):
        query = self._validate_vector(
            query_vector
        )

        if not isinstance(top_k, int) or top_k <= 0:
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

        if filters is None:
            filters = {}

        if not isinstance(filters, dict):
            raise TypeError(
                "filters must be dict or None"
            )

        scored = []
        order_index = 0

        while order_index < len(self._order):
            item_id = self._order[
                order_index
            ]

            entry = self._entries[
                item_id
            ]

            if self._matches_filters(
                entry,
                filters,
            ):
                score = self.metric.score(
                    query,
                    entry.vector,
                )

                if (
                    min_score is None
                    or score >= min_score
                ):
                    scored.append(
                        (
                            score,
                            order_index,
                            entry,
                        )
                    )

            order_index += 1

        scored.sort(
            key=lambda row: (
                -row[0],
                row[1],
            )
        )

        if len(scored) > top_k:
            scored = scored[:top_k]

        results = []
        rank = 1

        for score, original_index, entry in scored:
            results.append(
                IndexSearchResult(
                    entry=entry,
                    score=score,
                    rank=rank,
                )
            )

            rank += 1

        return results

    def state_dict(self):
        entries = []

        for item_id in self._order:
            entries.append(
                self._entries[
                    item_id
                ].to_dict()
            )

        return {
            "type": "FlatVectorIndex",
            "dimension": self.dimension,
            "entries": entries,
        }

    def load_state_dict(self, state):
        if not isinstance(state, dict):
            raise TypeError(
                "state must be dict"
            )

        if state.get("type") not in (
            None,
            "FlatVectorIndex",
        ):
            raise ValueError(
                "index state type mismatch"
            )

        dimension = int(
            state["dimension"]
        )

        if dimension != self.dimension:
            raise ValueError(
                "index dimension mismatch"
            )

        staged = FlatVectorIndex(
            dimension=self.dimension,
            metric=self.metric,
        )

        for row in state["entries"]:
            staged.add(
                IndexEntry(
                    item_id=row["item_id"],
                    vector=row["vector"],
                    text=row.get(
                        "text",
                        "",
                    ),
                    document_id=row.get(
                        "document_id"
                    ),
                    dataset_id=row.get(
                        "dataset_id"
                    ),
                    metadata=row.get(
                        "metadata",
                        {},
                    ),
                    provenance=row.get(
                        "provenance",
                        {},
                    ),
                )
            )

        self._entries = staged._entries
        self._order = staged._order
        return self

    def _validate_entry(self, entry):
        if not isinstance(
            entry,
            IndexEntry,
        ):
            raise TypeError(
                "entry must be IndexEntry"
            )

        if entry.dimension() != self.dimension:
            raise ValueError(
                "entry vector dimension mismatch"
            )

    def _validate_vector(
        self,
        vector,
    ):
        if hasattr(vector, "vector"):
            vector = vector.vector

        if not isinstance(
            vector,
            (list, tuple),
        ):
            raise TypeError(
                "query vector must be list/tuple or expose .vector"
            )

        if len(vector) != self.dimension:
            raise ValueError(
                "query vector dimension mismatch"
            )

        result = []

        for value in vector:
            if not isinstance(
                value,
                (int, float),
            ):
                raise TypeError(
                    "query vector values must be numeric"
                )

            result.append(
                float(value)
            )

        return result

    def _matches_filters(
        self,
        entry,
        filters,
    ):
        for key in filters:
            expected = filters[key]

            if key == "item_id":
                actual = entry.item_id

            elif key == "document_id":
                actual = entry.document_id

            elif key == "dataset_id":
                actual = entry.dataset_id

            elif key == "text":
                actual = entry.text

            else:
                if key not in entry.metadata:
                    return False

                actual = entry.metadata[
                    key
                ]

            if actual != expected:
                return False

        return True
