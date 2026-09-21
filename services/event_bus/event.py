class Event:
    """
    Deterministic event envelope.

    No timestamps/UUIDs are generated internally. Sequence and timestamp are
    supplied by the EventBus manager so tests and runtime behavior remain
    reproducible.
    """

    def __init__(
        self,
        event_id,
        topic,
        sequence,
        timestamp,
        payload=None,
        metadata=None,
        source_service=None,
        trace_id=None,
        correlation_id=None,
    ):
        if not isinstance(event_id, str) or event_id == "":
            raise ValueError("event_id must be non-empty str")

        if not isinstance(topic, str) or topic == "":
            raise ValueError("topic must be non-empty str")

        if not isinstance(sequence, int) or sequence <= 0:
            raise ValueError("sequence must be positive int")

        if not isinstance(timestamp, int) or timestamp < 0:
            raise ValueError("timestamp must be non-negative int")

        if payload is None:
            payload = {}

        if metadata is None:
            metadata = {}

        if not isinstance(payload, dict):
            raise TypeError("payload must be dict or None")

        if not isinstance(metadata, dict):
            raise TypeError("metadata must be dict or None")

        self.event_id = event_id
        self.topic = topic
        self.sequence = sequence
        self.timestamp = timestamp
        self.payload = self._copy(payload)
        self.metadata = self._copy(metadata)
        self.source_service = source_service
        self.trace_id = trace_id
        self.correlation_id = correlation_id

    def to_dict(self):
        return {
            "event_id": self.event_id,
            "topic": self.topic,
            "sequence": self.sequence,
            "timestamp": self.timestamp,
            "payload": self._copy(self.payload),
            "metadata": self._copy(self.metadata),
            "source_service": self.source_service,
            "trace_id": self.trace_id,
            "correlation_id": self.correlation_id,
        }

    def _copy(self, value):
        if isinstance(value, dict):
            result = {}
            for key in value:
                result[key] = self._copy(value[key])
            return result

        if isinstance(value, list):
            return [self._copy(item) for item in value]

        if isinstance(value, tuple):
            return [self._copy(item) for item in value]

        return value
