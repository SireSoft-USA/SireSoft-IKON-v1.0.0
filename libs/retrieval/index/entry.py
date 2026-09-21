class IndexEntry:
    """
    One vector-index record with retrieval metadata and source provenance.

    Vector data is copied on ingestion so later mutation of caller-owned lists
    cannot silently corrupt the index.
    """

    def __init__(
        self,
        item_id,
        vector,
        text="",
        document_id=None,
        dataset_id=None,
        metadata=None,
        provenance=None,
    ):
        if not isinstance(item_id, str) or item_id == "":
            raise ValueError("item_id must be non-empty str")

        if not isinstance(text, str):
            raise TypeError("text must be str")

        if document_id is not None and not isinstance(document_id, str):
            raise TypeError("document_id must be str or None")

        if dataset_id is not None and not isinstance(dataset_id, str):
            raise TypeError("dataset_id must be str or None")

        self.item_id = item_id
        self.vector = self._vector(vector)
        self.text = text
        self.document_id = document_id
        self.dataset_id = dataset_id
        self.metadata = self._copy_dict(metadata)
        self.provenance = self._copy_dict(provenance)

    def dimension(self):
        return len(self.vector)

    def to_dict(self):
        return {
            "item_id": self.item_id,
            "vector": list(self.vector),
            "text": self.text,
            "document_id": self.document_id,
            "dataset_id": self.dataset_id,
            "metadata": self._deep_copy(self.metadata),
            "provenance": self._deep_copy(self.provenance),
        }

    def _vector(self, vector):
        if hasattr(vector, "vector"):
            vector = vector.vector

        if not isinstance(vector, (list, tuple)):
            raise TypeError(
                "vector must be list/tuple or expose .vector"
            )

        if len(vector) == 0:
            raise ValueError("vector must not be empty")

        result = []

        for value in vector:
            if not isinstance(value, (int, float)):
                raise TypeError("vector elements must be numeric")

            result.append(float(value))

        return result

    def _copy_dict(self, value):
        if value is None:
            return {}

        if not isinstance(value, dict):
            raise TypeError(
                "metadata/provenance must be dict or None"
            )

        return self._deep_copy(value)

    def _deep_copy(self, value):
        if isinstance(value, dict):
            result = {}

            for key in value:
                result[key] = self._deep_copy(value[key])

            return result

        if isinstance(value, list):
            return [
                self._deep_copy(item)
                for item in value
            ]

        if isinstance(value, tuple):
            return [
                self._deep_copy(item)
                for item in value
            ]

        return value


class IndexSearchResult:
    def __init__(
        self,
        entry,
        score,
        rank,
    ):
        self.entry = entry
        self.item_id = entry.item_id
        self.score = float(score)
        self.rank = int(rank)

    def to_dict(self):
        return {
            "item_id": self.item_id,
            "score": self.score,
            "rank": self.rank,
            "entry": self.entry.to_dict(),
        }
