class Conversation:
    """
    Canonical ordered conversation container.

    The class is intentionally storage-oriented, not model-oriented. It
    preserves message ordering and conversation-level source metadata.
    """

    def __init__(
        self,
        conversation_id=None,
        messages=None,
        title=None,
        metadata=None,
        raw=None,
    ):
        if conversation_id is not None and not isinstance(conversation_id, str):
            raise TypeError("conversation_id must be str or None")
        if title is not None and not isinstance(title, str):
            raise TypeError("title must be str or None")
        if metadata is not None and not isinstance(metadata, dict):
            raise TypeError("metadata must be dict or None")

        self.conversation_id = conversation_id
        self.title = title
        self.metadata = {} if metadata is None else self._copy_dict(metadata)
        self.raw = raw
        self._messages = []

        if messages is not None:
            for message in messages:
                self.add_message(message)

    def _copy_dict(self, value):
        result = {}
        for key in value:
            result[key] = value[key]
        return result

    def add_message(self, message):
        if not hasattr(message, "role") or not hasattr(message, "content"):
            raise TypeError("message must provide role and content")
        self._messages.append(message)
        return len(self._messages) - 1

    def insert_message(self, index, message):
        if not isinstance(index, int):
            raise TypeError("index must be int")
        if not hasattr(message, "role") or not hasattr(message, "content"):
            raise TypeError("message must provide role and content")
        if index < 0 or index > len(self._messages):
            raise IndexError("message index out of bounds")
        self._messages.insert(index, message)

    def remove_message(self, index):
        if not isinstance(index, int):
            raise TypeError("index must be int")
        if index < 0 or index >= len(self._messages):
            raise IndexError("message index out of bounds")
        return self._messages.pop(index)

    def get_message(self, index):
        if not isinstance(index, int):
            raise TypeError("index must be int")
        if index < 0 or index >= len(self._messages):
            raise IndexError("message index out of bounds")
        return self._messages[index]

    def messages(self):
        return list(self._messages)

    def message_count(self):
        return len(self._messages)

    def character_count(self):
        total = 0
        for message in self._messages:
            total += len(message.content)
        return total

    def roles(self):
        result = []
        for message in self._messages:
            result.append(message.role)
        return result

    def to_dict(self):
        serialized = []
        for message in self._messages:
            if hasattr(message, "to_dict"):
                serialized.append(message.to_dict())
            else:
                serialized.append({
                    "role": message.role,
                    "content": message.content,
                })

        return {
            "conversation_id": self.conversation_id,
            "title": self.title,
            "metadata": self._copy_dict(self.metadata),
            "raw": self.raw,
            "messages": serialized,
        }

    def __len__(self):
        return len(self._messages)
