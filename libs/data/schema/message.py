class Message:
    """
    Canonical conversational message.

    Keeps both normalized content and source-preserved metadata so adapters can
    map different dialogue datasets without dropping source information.
    """

    VALID_ROLES = (
        "system",
        "user",
        "assistant",
        "tool",
        "unknown",
    )

    def __init__(
        self,
        role,
        content,
        name=None,
        metadata=None,
        source_index=None,
        raw=None,
    ):
        if not isinstance(role, str):
            raise TypeError("role must be str")
        if not isinstance(content, str):
            raise TypeError("content must be str")
        if role not in self.VALID_ROLES:
            raise ValueError("invalid message role: " + role)
        if name is not None and not isinstance(name, str):
            raise TypeError("name must be str or None")
        if metadata is not None and not isinstance(metadata, dict):
            raise TypeError("metadata must be dict or None")
        if source_index is not None and not isinstance(source_index, int):
            raise TypeError("source_index must be int or None")

        self.role = role
        self.content = content
        self.name = name
        self.metadata = {} if metadata is None else self._copy_dict(metadata)
        self.source_index = source_index
        self.raw = raw

    def _copy_dict(self, value):
        result = {}
        for key in value:
            result[key] = value[key]
        return result

    def clone(self):
        return Message(
            role=self.role,
            content=self.content,
            name=self.name,
            metadata=self.metadata,
            source_index=self.source_index,
            raw=self.raw,
        )

    def to_dict(self):
        return {
            "role": self.role,
            "content": self.content,
            "name": self.name,
            "metadata": self._copy_dict(self.metadata),
            "source_index": self.source_index,
            "raw": self.raw,
        }

    def is_empty(self):
        return self.content == ""

    def character_count(self):
        return len(self.content)

    def __repr__(self):
        return "Message(role=" + repr(self.role) + ", content=" + repr(self.content) + ")"
