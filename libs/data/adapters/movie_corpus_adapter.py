class MovieCorpusAdapter:
    """
    Adapter for Cornell Movie-Dialogs style data.

    Supports both:
      - a conversation record already containing utterance records/text
      - an ordered list of utterances supplied directly
    """

    def __init__(self, CanonicalRecord, Conversation, Message):
        self.CanonicalRecord = CanonicalRecord
        self.Conversation = Conversation
        self.Message = Message

    def adapt_conversation(self, record, index, source_file="conversations.json"):
        if not isinstance(record, dict):
            raise TypeError("movie conversation record must be dict")
        if not isinstance(index, int) or index < 0:
            raise ValueError("index must be non-negative int")

        utterances = self._extract_utterances(record)
        messages = []

        i = 0
        while i < len(utterances):
            item = utterances[i]

            if isinstance(item, dict):
                text = self._extract_text(item)
                speaker = self._extract_speaker(item)
                raw_item = self._copy_value(item)
            else:
                text = str(item)
                speaker = None
                raw_item = item

            role = "user" if i % 2 == 0 else "assistant"
            metadata = {}
            if speaker is not None:
                metadata["speaker"] = speaker

            messages.append(
                self.Message(
                    role,
                    text,
                    name=speaker,
                    metadata=metadata,
                    source_index=i,
                    raw=raw_item,
                )
            )
            i += 1

        conversation_id = self._first_nonempty(
            record.get("conversation_id"),
            record.get("id"),
            record.get("conversationID"),
            "movie-" + str(index),
        )

        conversation = self.Conversation(
            conversation_id=str(conversation_id),
            messages=messages,
            metadata=self._conversation_metadata(record),
            raw=self._copy_value(record),
        )

        return self.CanonicalRecord(
            record_id="movie-" + str(index),
            dataset_id="movie-corpus",
            dataset_name="Cornell Movie Dialogs Corpus",
            source_file=source_file,
            source_record_index=index,
            source_format="json",
            raw_content="\n".join(message.content for message in messages),
            normalized_content=self._conversation_text(messages),
            original_fields=self._copy_value(record),
            labels=["conversation", "movie_dialogue"],
            language="en",
            document_type="conversation",
            source_type="public_dataset",
            provenance={
                "dataset": "Cornell Movie Dialogs Corpus",
                "source_record_index": index,
            },
            split="unsplit",
            conversation=conversation,
            metadata={
                "turn_count": len(messages),
                "adapter": "MovieCorpusAdapter",
            },
        )

    def adapt_utterance(self, utterance, index, source_file="utterances.json"):
        if not isinstance(utterance, dict):
            raise TypeError("utterance must be dict")

        text = self._extract_text(utterance)
        speaker = self._extract_speaker(utterance)

        return self.CanonicalRecord(
            record_id="movie-utterance-" + str(index),
            dataset_id="movie-corpus",
            dataset_name="Cornell Movie Dialogs Corpus",
            source_file=source_file,
            source_record_index=index,
            source_format="json",
            raw_content=text,
            normalized_content=text,
            original_fields=self._copy_value(utterance),
            labels=["movie_utterance"],
            language="en",
            document_type="utterance",
            source_type="public_dataset",
            provenance={"dataset": "Cornell Movie Dialogs Corpus"},
            split="unsplit",
            metadata={
                "speaker": speaker,
                "adapter": "MovieCorpusAdapter",
            },
        )

    def _extract_utterances(self, record):
        keys = ("utterances", "lines", "dialogue", "dialog", "turns")
        for key in keys:
            value = record.get(key)
            if isinstance(value, list):
                return self._copy_value(value)
        raise ValueError("conversation record contains no utterance list")

    def _extract_text(self, item):
        for key in ("text", "utterance", "line", "content"):
            if key in item and item[key] is not None:
                return str(item[key])
        raise ValueError("utterance contains no text field")

    def _extract_speaker(self, item):
        for key in ("speaker", "speaker_id", "character", "character_id", "name"):
            if key in item and item[key] is not None:
                return str(item[key])
        return None

    def _conversation_metadata(self, record):
        metadata = {}
        for key in ("movie_id", "movieID", "genre", "title", "speaker_a", "speaker_b"):
            if key in record:
                metadata[key] = self._copy_value(record[key])
        return metadata

    def _conversation_text(self, messages):
        parts = []
        for message in messages:
            parts.append("<" + message.role.upper() + ">")
            parts.append(message.content)
        return "\n".join(parts)

    def _first_nonempty(self, *values):
        for value in values:
            if value is not None and value != "":
                return value
        return None

    def _copy_value(self, value):
        if isinstance(value, dict):
            out = {}
            for key in value:
                out[key] = self._copy_value(value[key])
            return out
        if isinstance(value, list):
            return [self._copy_value(item) for item in value]
        return value
