class DailyDialogAdapter:
    """
    Converts DailyDialog records into CanonicalRecord objects.

    The adapter does not delete or overwrite source fields. The original
    record is preserved in original_fields, while normalized_content is a
    separate model-facing representation.
    """

    def __init__(self, CanonicalRecord, Conversation, Message):
        self.CanonicalRecord = CanonicalRecord
        self.Conversation = Conversation
        self.Message = Message

    def adapt_record(self, record, index, source_file="dialogues.json"):
        if not isinstance(record, dict):
            raise TypeError("DailyDialog record must be dict")
        if not isinstance(index, int) or index < 0:
            raise ValueError("index must be non-negative int")

        turns = self._extract_turns(record)
        acts = self._copy_sequence(record.get("act", record.get("acts", [])))
        emotions = self._copy_sequence(record.get("emotion", record.get("emotions", [])))

        messages = []
        i = 0
        while i < len(turns):
            role = "user" if i % 2 == 0 else "assistant"
            metadata = {}

            if i < len(acts):
                metadata["dialog_act"] = acts[i]
            if i < len(emotions):
                metadata["emotion"] = emotions[i]

            messages.append(
                self.Message(
                    role=role,
                    content=str(turns[i]),
                    metadata=metadata,
                    source_index=i,
                    raw=turns[i],
                )
            )
            i += 1

        conversation = self.Conversation(
            conversation_id="dailydialog-" + str(index),
            messages=messages,
            metadata={"dataset": "DailyDialog"},
            raw=self._copy_value(record),
        )

        normalized = self._conversation_text(messages)

        return self.CanonicalRecord(
            record_id="dailydialog-" + str(index),
            dataset_id="dailydialog",
            dataset_name="DailyDialog",
            source_file=source_file,
            source_record_index=index,
            source_format="json",
            raw_content=self._best_raw_text(record, turns),
            normalized_content=normalized,
            original_fields=self._copy_value(record),
            labels=["conversation", "daily_dialogue"],
            language="en",
            document_type="conversation",
            source_type="public_dataset",
            provenance={
                "dataset": "DailyDialog",
                "source_record_index": index,
            },
            split="unsplit",
            conversation=conversation,
            metadata={
                "turn_count": len(messages),
                "adapter": "DailyDialogAdapter",
            },
        )

    def _extract_turns(self, record):
        candidates = (
            record.get("dialogue"),
            record.get("dialog"),
            record.get("turns"),
            record.get("utterances"),
        )

        i = 0
        while i < len(candidates):
            value = candidates[i]
            if isinstance(value, list):
                return self._copy_sequence(value)
            i += 1

        raise ValueError("DailyDialog record contains no supported turn list")

    def _conversation_text(self, messages):
        parts = []
        for message in messages:
            parts.append("<" + message.role.upper() + ">")
            parts.append(message.content)
        return "\n".join(parts)

    def _best_raw_text(self, record, turns):
        if "raw" in record and isinstance(record["raw"], str):
            return record["raw"]
        return "\n".join(str(item) for item in turns)

    def _copy_sequence(self, value):
        if value is None:
            return []
        if not isinstance(value, (list, tuple)):
            return []
        out = []
        for item in value:
            out.append(self._copy_value(item))
        return out

    def _copy_value(self, value):
        if isinstance(value, dict):
            out = {}
            for key in value:
                out[key] = self._copy_value(value[key])
            return out
        if isinstance(value, list):
            out = []
            for item in value:
                out.append(self._copy_value(item))
            return out
        if isinstance(value, tuple):
            out = []
            for item in value:
                out.append(self._copy_value(item))
            return out
        return value
