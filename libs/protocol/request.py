class ServiceRequest:
    """
    Typed request contract used between SireLLM services.
    """

    def __init__(
        self,
        request_id,
        service,
        operation,
        payload=None,
        metadata=None,
        correlation_id=None,
        trace_id=None,
    ):
        if not isinstance(request_id, str) or request_id == "":
            raise ValueError("request_id must be non-empty str")

        if not isinstance(service, str) or service == "":
            raise ValueError("service must be non-empty str")

        if not isinstance(operation, str) or operation == "":
            raise ValueError("operation must be non-empty str")

        if payload is None:
            payload = {}

        if metadata is None:
            metadata = {}

        if not isinstance(payload, dict):
            raise TypeError("payload must be dict or None")

        if not isinstance(metadata, dict):
            raise TypeError("metadata must be dict or None")

        self.request_id = request_id
        self.service = service
        self.operation = operation
        self.payload = self._copy(payload)
        self.metadata = self._copy(metadata)
        self.correlation_id = correlation_id
        self.trace_id = trace_id

    def to_dict(self):
        return {
            "request_id": self.request_id,
            "service": self.service,
            "operation": self.operation,
            "payload": self._copy(self.payload),
            "metadata": self._copy(self.metadata),
            "correlation_id": self.correlation_id,
            "trace_id": self.trace_id,
        }

    def to_message(self):
        return ProtocolMessage(
            message_id=self.request_id,
            message_type="request",
            service=self.service,
            payload={
                "operation": self.operation,
                "payload": self._copy(self.payload),
                "metadata": self._copy(self.metadata),
            },
            correlation_id=self.correlation_id,
            trace_id=self.trace_id,
        )

    @classmethod
    def from_message(cls, message):
        if not isinstance(message, ProtocolMessage):
            raise TypeError("message must be ProtocolMessage")

        if message.message_type != "request":
            raise ValueError("message is not a request")

        body = message.payload

        return cls(
            request_id=message.message_id,
            service=message.service,
            operation=body["operation"],
            payload=body.get("payload", {}),
            metadata=body.get("metadata", {}),
            correlation_id=message.correlation_id,
            trace_id=message.trace_id,
        )

    def _copy(self, value):
        if isinstance(value, dict):
            result = {}

            for key in value:
                result[key] = self._copy(value[key])

            return result

        if isinstance(value, list):
            return [
                self._copy(item)
                for item in value
            ]

        if isinstance(value, tuple):
            return [
                self._copy(item)
                for item in value
            ]

        return value
