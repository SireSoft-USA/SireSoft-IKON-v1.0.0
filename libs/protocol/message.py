class ProtocolMessage:
    """
    Generic SireLLM internal message envelope.

    message_type:
      request
      response
      event
      error
    """

    VALID_TYPES = (
        "request",
        "response",
        "event",
        "error",
    )

    def __init__(
        self,
        message_id,
        message_type,
        service,
        payload=None,
        headers=None,
        correlation_id=None,
        trace_id=None,
        protocol_version="1.0",
    ):
        if not isinstance(message_id, str) or message_id == "":
            raise ValueError("message_id must be non-empty str")

        if message_type not in self.VALID_TYPES:
            raise ValueError("invalid message_type")

        if not isinstance(service, str) or service == "":
            raise ValueError("service must be non-empty str")

        if payload is None:
            payload = {}

        if headers is None:
            headers = {}

        if not isinstance(payload, dict):
            raise TypeError("payload must be dict or None")

        if not isinstance(headers, dict):
            raise TypeError("headers must be dict or None")

        if correlation_id is not None and not isinstance(correlation_id, str):
            raise TypeError("correlation_id must be str or None")

        if trace_id is not None and not isinstance(trace_id, str):
            raise TypeError("trace_id must be str or None")

        if not isinstance(protocol_version, str) or protocol_version == "":
            raise ValueError("protocol_version must be non-empty str")

        self.message_id = message_id
        self.message_type = message_type
        self.service = service
        self.payload = self._deep_copy(payload)
        self.headers = self._deep_copy(headers)
        self.correlation_id = correlation_id
        self.trace_id = trace_id
        self.protocol_version = protocol_version

    def to_dict(self):
        return {
            "message_id": self.message_id,
            "message_type": self.message_type,
            "service": self.service,
            "payload": self._deep_copy(self.payload),
            "headers": self._deep_copy(self.headers),
            "correlation_id": self.correlation_id,
            "trace_id": self.trace_id,
            "protocol_version": self.protocol_version,
        }

    @classmethod
    def from_dict(cls, value):
        if not isinstance(value, dict):
            raise TypeError("message payload must be dict")

        return cls(
            message_id=value["message_id"],
            message_type=value["message_type"],
            service=value["service"],
            payload=value.get("payload", {}),
            headers=value.get("headers", {}),
            correlation_id=value.get("correlation_id"),
            trace_id=value.get("trace_id"),
            protocol_version=value.get(
                "protocol_version",
                "1.0",
            ),
        )

    def _deep_copy(self, value):
        if isinstance(value, dict):
            result = {}

            for key in value:
                result[key] = self._deep_copy(value[key])

            return result

        if isinstance(value, list):
            return [
                self._deep_copy(item)
                for item in value
            ]

        if isinstance(value, tuple):
            return [
                self._deep_copy(item)
                for item in value
            ]

        return value
