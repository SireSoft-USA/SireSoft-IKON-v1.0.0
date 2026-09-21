class OpenAssistantAdapter:
    """
    Adapter for OASST1 ready-message style records.

    It supports:
      - single message preservation
      - reconstruction of a conversation when an ordered message path is given

    OASST roles are mapped:
      prompter -> user
      assistant -> assistant
      system -> system
      other/unknown -> unknown
    """

    def __init__(self, CanonicalRecord, Conversation, Message):
        self.CanonicalRecord = CanonicalRecord
        self.Conversation = Conversation
        self.Message = Message

    def adapt_message(self, record, index, source_file="oasst1-ready.jsonl"):
        if not isinstance(record, dict):
            raise TypeError("OpenAssistant message record must be dict")

        text = self._extract_text(record)
        source_role = self._extract_role(record)
        mapped_role = self._map_role(source_role)

        message = self.Message(
            mapped_role,
            text,
            metadata={
                "source_role": source_role,
                "message_id": record.get("message_id"),
                "parent_id": record.get("parent_id"),
            },
            source_index=index,
            raw=self._copy_value(record),
        )

        conversation = self.Conversation(
            conversation_id=self._conversation_id(record, index),
            messages=[message],
            metadata={
                "tree_id": record.get("message_tree_id", record.get("tree_id")),
            },
            raw=self._copy_value(record),
        )

        return self.CanonicalRecord(
            record_id="openassistant-message-" + str(index),
            dataset_id="openassistant",
            dataset_name="OpenAssistant OASST1",
            source_file=source_file,
            source_record_index=index,
            source_format="jsonl",
            raw_content=text,
            normalized_content="<" + mapped_role.upper() + ">\n" + text,
            original_fields=self._copy_value(record),
            labels=["assistant_dialogue", "oasst1"],
            language=str(record.get("lang", "en")),
            document_type="message",
            source_type="public_dataset",
            provenance={
                "dataset": "OpenAssistant OASST1",
                "message_id": record.get("message_id"),
                "parent_id": record.get("parent_id"),
            },
            split="unsplit",
            conversation=conversation,
            metadata={
                "source_role": source_role,
                "adapter": "OpenAssistantAdapter",
            },
        )

    def adapt_conversation(self, records, index, source_file="oasst1-ready.jsonl"):
        if not isinstance(records, list):
            raise TypeError("records must be list")

        messages = []
        original = []

        i = 0
        while i < len(records):
            record = records[i]
            if not isinstance(record, dict):
                raise TypeError("every OASST conversation record must be dict")

            text = self._extract_text(record)
            source_role = self._extract_role(record)
            mapped_role = self._map_role(source_role)

            messages.append(
                self.Message(
                    mapped_role,
                    text,
                    metadata={
                        "source_role": source_role,
                        "message_id": record.get("message_id"),
                        "parent_id": record.get("parent_id"),
                    },
                    source_index=i,
                    raw=self._copy_value(record),
                )
            )
            original.append(self._copy_value(record))
            i += 1

        conversation_id = "oasst-conversation-" + str(index)
        if len(records) > 0:
            conversation_id = self._conversation_id(records[0], index)

        conversation = self.Conversation(
            conversation_id=conversation_id,
            messages=messages,
            metadata={"message_count": len(messages)},
            raw=original,
        )

        return self.CanonicalRecord(
            record_id="openassistant-conversation-" + str(index),
            dataset_id="openassistant",
            dataset_name="OpenAssistant OASST1",
            source_file=source_file,
            source_record_index=index,
            source_format="jsonl",
            raw_content="\n".join(message.content for message in messages),
            normalized_content=self._conversation_text(messages),
            original_fields={"messages": original},
            labels=["assistant_dialogue", "multi_turn", "oasst1"],
            language=self._conversation_language(records),
            document_type="conversation",
            source_type="public_dataset",
            provenance={
                "dataset": "OpenAssistant OASST1",
                "message_count": len(messages),
            },
            split="unsplit",
            conversation=conversation,
            metadata={
                "turn_count": len(messages),
                "adapter": "OpenAssistantAdapter",
            },
        )

    def _extract_text(self, record):
        for key in ("text", "content", "message"):
            value = record.get(key)
            if value is not None:
                return str(value)
        raise ValueError("OpenAssistant message contains no text")

    def _extract_role(self, record):
        value = record.get("role", record.get("speaker", "unknown"))
        return str(value)

    def _map_role(self, role):
        lower = role.lower()
        if lower == "prompter" or lower == "user" or lower == "human":
            return "user"
        if lower == "assistant" or lower == "bot":
            return "assistant"
        if lower == "system":
            return "system"
        if lower == "tool":
            return "tool"
        return "unknown"

    def _conversation_id(self, record, index):
        for key in ("message_tree_id", "tree_id", "conversation_id"):
            value = record.get(key)
            if value is not None and value != "":
                return str(value)
        return "oasst-" + str(index)

    def _conversation_language(self, records):
        if len(records) == 0:
            return "unknown"
        first = records[0].get("lang")
        if first is None:
            return "unknown"
        return str(first)

    def _conversation_text(self, messages):
        parts = []
        for message in messages:
            parts.append("<" + message.role.upper() + ">")
            parts.append(message.content)
        return "\n".join(parts)

    def _copy_value(self, value):
        if isinstance(value, dict):
            out = {}
            for key in value:
                out[key] = self._copy_value(value[key])
            return out
        if isinstance(value, list):
            return [self._copy_value(item) for item in value]
        return value
