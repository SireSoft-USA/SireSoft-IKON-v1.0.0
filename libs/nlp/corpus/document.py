class Document:
    """
    Corpus-level immutable-ish document view.

    The data/schema layer owns canonical source preservation. This class is a
    lightweight NLP-facing representation used for corpus operations such as
    splitting, deduplication, tokenization, retrieval preparation, and stats.
    """

    def __init__(
        self,
        document_id,
        text,
        dataset_id,
        source_record_id=None,
        metadata=None,
        labels=None,
        split="unsplit",
        provenance=None,
    ):
        if not isinstance(document_id, str) or document_id == "":
            raise ValueError("document_id must be non-empty str")
        if not isinstance(text, str):
            raise TypeError("text must be str")
        if not isinstance(dataset_id, str) or dataset_id == "":
            raise ValueError("dataset_id must be non-empty str")
        if source_record_id is not None and not isinstance(source_record_id, str):
            raise TypeError("source_record_id must be str or None")
        if metadata is not None and not isinstance(metadata, dict):
            raise TypeError("metadata must be dict or None")
        if labels is not None and not isinstance(labels, list):
            raise TypeError("labels must be list or None")
        if provenance is not None and not isinstance(provenance, dict):
            raise TypeError("provenance must be dict or None")
        if split not in ("train", "validation", "test", "unsplit"):
            raise ValueError("invalid split")

        self.document_id = document_id
        self.text = text
        self.dataset_id = dataset_id
        self.source_record_id = source_record_id
        self.metadata = self._copy_dict(metadata)
        self.labels = self._copy_list(labels)
        self.split = split
        self.provenance = self._copy_dict(provenance)

    def _copy_dict(self, value):
        if value is None:
            return {}
        out = {}
        for key in value:
            out[key] = self._deep_copy(value[key])
        return out

    def _copy_list(self, value):
        if value is None:
            return []
        return [self._deep_copy(item) for item in value]

    def _deep_copy(self, value):
        if isinstance(value, dict):
            out = {}
            for key in value:
                out[key] = self._deep_copy(value[key])
            return out
        if isinstance(value, list):
            return [self._deep_copy(item) for item in value]
        if isinstance(value, tuple):
            return [self._deep_copy(item) for item in value]
        return value

    def character_count(self):
        return len(self.text)

    def is_empty(self):
        return self.text == ""

    def add_label(self, label):
        if not isinstance(label, str) or label == "":
            raise ValueError("label must be non-empty str")
        if label not in self.labels:
            self.labels.append(label)

    def set_split(self, split):
        if split not in ("train", "validation", "test", "unsplit"):
            raise ValueError("invalid split")
        self.split = split

    def to_dict(self):
        return {
            "document_id": self.document_id,
            "text": self.text,
            "dataset_id": self.dataset_id,
            "source_record_id": self.source_record_id,
            "metadata": self._copy_dict(self.metadata),
            "labels": self._copy_list(self.labels),
            "split": self.split,
            "provenance": self._copy_dict(self.provenance),
        }

    @classmethod
    def from_canonical_record(cls, record):
        if record is None:
            raise ValueError("record is required")

        text = ""
        if hasattr(record, "training_text"):
            text = record.training_text()
        elif hasattr(record, "normalized_content") and record.normalized_content is not None:
            text = record.normalized_content
        elif hasattr(record, "raw_content") and record.raw_content is not None:
            text = record.raw_content

        metadata = {}
        if hasattr(record, "metadata") and isinstance(record.metadata, dict):
            for key in record.metadata:
                metadata[key] = record.metadata[key]

        provenance = {}
        if hasattr(record, "provenance") and isinstance(record.provenance, dict):
            for key in record.provenance:
                provenance[key] = record.provenance[key]

        labels = []
        if hasattr(record, "labels") and isinstance(record.labels, list):
            labels = list(record.labels)

        split = getattr(record, "split", "unsplit")
        if split is None:
            split = "unsplit"

        return cls(
            document_id=str(record.record_id),
            text=text,
            dataset_id=str(record.dataset_id),
            source_record_id=str(record.record_id),
            metadata=metadata,
            labels=labels,
            split=split,
            provenance=provenance,
        )
