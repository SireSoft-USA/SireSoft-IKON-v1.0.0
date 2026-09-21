class CorpusConversation:
    """
    NLP-facing conversation representation for corpus construction.

    This is separate from data/schema/conversation.py:
    - schema conversation preserves source structure
    - corpus conversation prepares model-facing turn sequences
    """

    def __init__(
        self,
        conversation_id,
        dataset_id,
        turns=None,
        metadata=None,
        source_record_id=None,
    ):
        if not isinstance(conversation_id, str) or conversation_id == "":
            raise ValueError("conversation_id must be non-empty str")
        if not isinstance(dataset_id, str) or dataset_id == "":
            raise ValueError("dataset_id must be non-empty str")
        if metadata is not None and not isinstance(metadata, dict):
            raise TypeError("metadata must be dict or None")

        self.conversation_id = conversation_id
        self.dataset_id = dataset_id
        self.source_record_id = source_record_id
        self.metadata = {} if metadata is None else dict(metadata)
        self._turns = []

        if turns is not None:
            for turn in turns:
                self.add_turn(turn)

    def add_turn(self, turn):
        if not hasattr(turn, "role") or not hasattr(turn, "content"):
            raise TypeError("turn must provide role and content")
        self._turns.append(turn)

    def turns(self):
        return list(self._turns)

    def turn_count(self):
        return len(self._turns)

    def roles(self):
        return [turn.role for turn in self._turns]

    def to_training_text(self):
        parts = []

        for turn in self._turns:
            role = str(turn.role).upper()
            parts.append("<" + role + ">")
            parts.append(turn.content)

        return "\n".join(parts)

    def character_count(self):
        total = 0
        for turn in self._turns:
            total += len(turn.content)
        return total

    def to_dict(self):
        turn_rows = []

        for turn in self._turns:
            if hasattr(turn, "to_dict"):
                turn_rows.append(turn.to_dict())
            else:
                turn_rows.append({
                    "role": turn.role,
                    "content": turn.content,
                })

        return {
            "conversation_id": self.conversation_id,
            "dataset_id": self.dataset_id,
            "source_record_id": self.source_record_id,
            "metadata": dict(self.metadata),
            "turns": turn_rows,
        }

    @classmethod
    def from_schema_conversation(
        cls,
        conversation,
        dataset_id,
        source_record_id=None,
    ):
        if conversation is None:
            raise ValueError("conversation is required")
        if not hasattr(conversation, "messages"):
            raise TypeError("conversation must provide messages()")

        conversation_id = getattr(conversation, "conversation_id", None)
        if conversation_id is None or conversation_id == "":
            conversation_id = str(source_record_id)

        instance = cls(
            conversation_id=str(conversation_id),
            dataset_id=dataset_id,
            metadata=getattr(conversation, "metadata", {}),
            source_record_id=source_record_id,
        )

        for message in conversation.messages():
            instance.add_turn(message)

        return instance
