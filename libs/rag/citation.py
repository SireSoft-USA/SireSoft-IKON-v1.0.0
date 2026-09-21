class Citation:
    """
    Source reference carried from retrieval into the final RAG response.
    """

    def __init__(
        self,
        citation_id,
        item_id,
        document_id=None,
        dataset_id=None,
        text="",
        score=None,
        metadata=None,
        provenance=None,
    ):
        if not isinstance(citation_id, str) or citation_id == "":
            raise ValueError("citation_id must be non-empty str")
        if not isinstance(item_id, str) or item_id == "":
            raise ValueError("item_id must be non-empty str")
        if not isinstance(text, str):
            raise TypeError("text must be str")

        if score is not None and not isinstance(score, (int, float)):
            raise TypeError("score must be numeric or None")

        self.citation_id = citation_id
        self.item_id = item_id
        self.document_id = document_id
        self.dataset_id = dataset_id
        self.text = text
        self.score = None if score is None else float(score)
        self.metadata = self._copy_dict(metadata)
        self.provenance = self._copy_dict(provenance)

    def marker(self):
        return "[" + self.citation_id + "]"

    def to_dict(self):
        return {
            "citation_id": self.citation_id,
            "marker": self.marker(),
            "item_id": self.item_id,
            "document_id": self.document_id,
            "dataset_id": self.dataset_id,
            "text": self.text,
            "score": self.score,
            "metadata": self._copy_dict(self.metadata),
            "provenance": self._copy_dict(self.provenance),
        }

    def _copy_dict(self, value):
        if value is None:
            return {}

        if not isinstance(value, dict):
            raise TypeError("metadata/provenance must be dict or None")

        result = {}

        for key in value:
            result[key] = self._deep_copy(value[key])

        return result

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


class CitationBuilder:
    """
    Converts ranked retrieval results into stable [S1], [S2], ... citations.
    """

    def build(self, ranked_results):
        citations = []
        index = 0

        for result in ranked_results:
            if not hasattr(result, "entry"):
                raise TypeError("ranked result must expose entry")

            entry = result.entry

            score = None

            if hasattr(result, "rerank_score"):
                score = result.rerank_score
            elif hasattr(result, "score"):
                score = result.score

            citations.append(
                Citation(
                    citation_id="S" + str(index + 1),
                    item_id=entry.item_id,
                    document_id=entry.document_id,
                    dataset_id=entry.dataset_id,
                    text=entry.text,
                    score=score,
                    metadata=getattr(entry, "metadata", {}),
                    provenance=getattr(entry, "provenance", {}),
                )
            )

            index += 1

        return citations
