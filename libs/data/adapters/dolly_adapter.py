class DollyAdapter:
    """
    Adapter for Databricks Dolly 15K-style JSONL records.
    """

    def __init__(self, CanonicalRecord, Conversation, Message):
        self.CanonicalRecord = CanonicalRecord
        self.Conversation = Conversation
        self.Message = Message

    def adapt_record(self, record, index, source_file="databricks-dolly-15k.jsonl"):
        if not isinstance(record, dict):
            raise TypeError("Dolly record must be dict")
        if not isinstance(index, int) or index < 0:
            raise ValueError("index must be non-negative int")

        instruction = self._as_text(record.get("instruction", ""))
        context = self._as_text(record.get("context", ""))
        response = self._as_text(record.get("response", ""))
        category = self._as_text(record.get("category", ""))

        user_content = instruction
        if context != "":
            if user_content != "":
                user_content += "\n\n"
            user_content += context

        messages = [
            self.Message(
                "user",
                user_content,
                metadata={"source_fields": ["instruction", "context"]},
                source_index=0,
                raw={
                    "instruction": record.get("instruction"),
                    "context": record.get("context"),
                },
            ),
            self.Message(
                "assistant",
                response,
                metadata={"source_field": "response"},
                source_index=1,
                raw=record.get("response"),
            ),
        ]

        conversation = self.Conversation(
            conversation_id="dolly-" + str(index),
            messages=messages,
            metadata={"category": category},
            raw=self._copy_value(record),
        )

        labels = ["instruction_following"]
        if category != "":
            labels.append(category)

        return self.CanonicalRecord(
            record_id="dolly-" + str(index),
            dataset_id="dolly",
            dataset_name="Databricks Dolly 15K",
            source_file=source_file,
            source_record_index=index,
            source_format="jsonl",
            raw_content=self._raw_text(record),
            normalized_content=self._normalized(user_content, response),
            original_fields=self._copy_value(record),
            labels=labels,
            language="en",
            document_type="instruction_response",
            source_type="public_dataset",
            provenance={
                "dataset": "Databricks Dolly 15K",
                "source_record_index": index,
            },
            split="unsplit",
            conversation=conversation,
            metadata={
                "category": category,
                "adapter": "DollyAdapter",
            },
        )

    def _normalized(self, user_content, response):
        return "<USER>\n" + user_content + "\n<ASSISTANT>\n" + response

    def _raw_text(self, record):
        instruction = self._as_text(record.get("instruction", ""))
        context = self._as_text(record.get("context", ""))
        response = self._as_text(record.get("response", ""))
        pieces = [instruction]
        if context != "":
            pieces.append(context)
        pieces.append(response)
        return "\n".join(pieces)

    def _as_text(self, value):
        if value is None:
            return ""
        return str(value)

    def _copy_value(self, value):
        if isinstance(value, dict):
            out = {}
            for key in value:
                out[key] = self._copy_value(value[key])
            return out
        if isinstance(value, list):
            return [self._copy_value(item) for item in value]
        return value
