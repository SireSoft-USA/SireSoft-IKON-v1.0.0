class CanonicalRecord:
    """
    Loss-preserving canonical record used across all six datasets.

    Two representations are kept deliberately:
      1. raw / original_fields  -> source-faithful preservation
      2. normalized_content     -> model/training representation

    This prevents preprocessing from silently destroying source information.
    """

    def __init__(
        self,
        record_id,
        dataset_id,
        dataset_name,
        source_file,
        source_record_index,
        source_format,
        raw_content=None,
        normalized_content=None,
        original_fields=None,
        labels=None,
        language=None,
        document_type=None,
        source_type=None,
        provenance=None,
        checksum=None,
        preprocessing_history=None,
        split=None,
        conversation=None,
        metadata=None,
    ):
        self._require_string("record_id", record_id)
        self._require_string("dataset_id", dataset_id)
        self._require_string("dataset_name", dataset_name)
        self._require_string("source_file", source_file)
        self._require_string("source_format", source_format)

        if not isinstance(source_record_index, int):
            raise TypeError("source_record_index must be int")
        if source_record_index < 0:
            raise ValueError("source_record_index must be >= 0")

        if raw_content is not None and not isinstance(raw_content, str):
            raise TypeError("raw_content must be str or None")
        if normalized_content is not None and not isinstance(normalized_content, str):
            raise TypeError("normalized_content must be str or None")
        if language is not None and not isinstance(language, str):
            raise TypeError("language must be str or None")
        if document_type is not None and not isinstance(document_type, str):
            raise TypeError("document_type must be str or None")
        if source_type is not None and not isinstance(source_type, str):
            raise TypeError("source_type must be str or None")
        if checksum is not None and not isinstance(checksum, (str, int)):
            raise TypeError("checksum must be str, int, or None")
        if split is not None and split not in ("train", "validation", "test", "unsplit"):
            raise ValueError("invalid split")

        self.record_id = record_id
        self.dataset_id = dataset_id
        self.dataset_name = dataset_name
        self.source_file = source_file
        self.source_record_index = source_record_index
        self.source_format = source_format

        self.raw_content = raw_content
        self.normalized_content = normalized_content
        self.original_fields = self._copy_dict(original_fields)
        self.labels = self._copy_list(labels)
        self.language = language
        self.document_type = document_type
        self.source_type = source_type
        self.provenance = self._copy_dict(provenance)
        self.checksum = checksum
        self.preprocessing_history = self._copy_list(preprocessing_history)
        self.split = split
        self.conversation = conversation
        self.metadata = self._copy_dict(metadata)

    def _require_string(self, name, value):
        if not isinstance(value, str):
            raise TypeError(name + " must be str")
        if value == "":
            raise ValueError(name + " must not be empty")

    def _copy_dict(self, value):
        if value is None:
            return {}
        if not isinstance(value, dict):
            raise TypeError("expected dict or None")
        result = {}
        for key in value:
            result[key] = value[key]
        return result

    def _copy_list(self, value):
        if value is None:
            return []
        if not isinstance(value, list):
            raise TypeError("expected list or None")
        result = []
        for item in value:
            result.append(item)
        return result

    def add_preprocessing_step(self, name, details=None):
        if not isinstance(name, str) or name == "":
            raise ValueError("preprocessing step name must be non-empty str")
        if details is not None and not isinstance(details, dict):
            raise TypeError("details must be dict or None")

        entry = {
            "name": name,
            "details": {} if details is None else self._copy_dict(details),
        }
        self.preprocessing_history.append(entry)

    def add_label(self, label):
        if not isinstance(label, str):
            raise TypeError("label must be str")
        if label not in self.labels:
            self.labels.append(label)

    def set_split(self, split):
        if split not in ("train", "validation", "test", "unsplit"):
            raise ValueError("invalid split")
        self.split = split

    def training_text(self):
        if self.normalized_content is not None:
            return self.normalized_content

        if self.conversation is not None:
            pieces = []
            messages = self.conversation.messages()
            for message in messages:
                pieces.append("<" + message.role.upper() + ">")
                pieces.append(message.content)
            return "\n".join(pieces)

        if self.raw_content is not None:
            return self.raw_content

        return ""

    def preserves_source(self):
        return (
            self.raw_content is not None
            or len(self.original_fields) > 0
            or self.conversation is not None
        )

    def to_dict(self):
        conversation_value = None
        if self.conversation is not None:
            if hasattr(self.conversation, "to_dict"):
                conversation_value = self.conversation.to_dict()
            else:
                conversation_value = self.conversation

        return {
            "record_id": self.record_id,
            "dataset_id": self.dataset_id,
            "dataset_name": self.dataset_name,
            "source_file": self.source_file,
            "source_record_index": self.source_record_index,
            "source_format": self.source_format,
            "raw_content": self.raw_content,
            "normalized_content": self.normalized_content,
            "original_fields": self._copy_dict(self.original_fields),
            "labels": self._copy_list(self.labels),
            "language": self.language,
            "document_type": self.document_type,
            "source_type": self.source_type,
            "provenance": self._copy_dict(self.provenance),
            "checksum": self.checksum,
            "preprocessing_history": self._copy_list(self.preprocessing_history),
            "split": self.split,
            "conversation": conversation_value,
            "metadata": self._copy_dict(self.metadata),
        }
