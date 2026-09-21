class Chunk:
    """
    Retrieval-ready chunk with explicit source offsets and provenance.
    """

    def __init__(
        self,
        chunk_id,
        document_id,
        dataset_id,
        text,
        chunk_index,
        char_start=None,
        char_end=None,
        token_start=None,
        token_end=None,
        metadata=None,
        provenance=None,
    ):
        if not isinstance(chunk_id, str) or chunk_id == "":
            raise ValueError("chunk_id must be non-empty str")
        if not isinstance(document_id, str) or document_id == "":
            raise ValueError("document_id must be non-empty str")
        if not isinstance(dataset_id, str) or dataset_id == "":
            raise ValueError("dataset_id must be non-empty str")
        if not isinstance(text, str):
            raise TypeError("text must be str")
        if not isinstance(chunk_index, int) or chunk_index < 0:
            raise ValueError("chunk_index must be non-negative int")

        self.chunk_id = chunk_id
        self.document_id = document_id
        self.dataset_id = dataset_id
        self.text = text
        self.chunk_index = chunk_index
        self.char_start = self._optional_offset(char_start, "char_start")
        self.char_end = self._optional_offset(char_end, "char_end")
        self.token_start = self._optional_offset(token_start, "token_start")
        self.token_end = self._optional_offset(token_end, "token_end")

        if (
            self.char_start is not None
            and self.char_end is not None
            and self.char_end < self.char_start
        ):
            raise ValueError("char_end cannot precede char_start")

        if (
            self.token_start is not None
            and self.token_end is not None
            and self.token_end < self.token_start
        ):
            raise ValueError("token_end cannot precede token_start")

        self.metadata = self._copy_dict(metadata)
        self.provenance = self._copy_dict(provenance)

    def _optional_offset(self, value, name):
        if value is None:
            return None
        if not isinstance(value, int) or value < 0:
            raise ValueError(name + " must be non-negative int or None")
        return value

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
            return [self._deep_copy(item) for item in value]

        if isinstance(value, tuple):
            return [self._deep_copy(item) for item in value]

        return value

    def character_count(self):
        return len(self.text)

    def is_empty(self):
        return self.text == ""

    def source_span(self):
        if self.char_start is not None and self.char_end is not None:
            return (self.char_start, self.char_end)

        if self.token_start is not None and self.token_end is not None:
            return (self.token_start, self.token_end)

        return None

    def to_dict(self):
        return {
            "chunk_id": self.chunk_id,
            "document_id": self.document_id,
            "dataset_id": self.dataset_id,
            "text": self.text,
            "chunk_index": self.chunk_index,
            "char_start": self.char_start,
            "char_end": self.char_end,
            "token_start": self.token_start,
            "token_end": self.token_end,
            "metadata": self._copy_dict(self.metadata),
            "provenance": self._copy_dict(self.provenance),
        }
