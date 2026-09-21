class ServiceResponse:
    """
    Typed response contract correlated to one ServiceRequest.
    """

    def __init__(
        self,
        request_id,
        service,
        success,
        data=None,
        error=None,
        metadata=None,
        correlation_id=None,
        trace_id=None,
    ):
        if not isinstance(request_id, str) or request_id == "":
            raise ValueError("request_id must be non-empty str")

        if not isinstance(service, str) or service == "":
            raise ValueError("service must be non-empty str")

        if not isinstance(success, bool):
            raise TypeError("success must be bool")

        if data is None:
            data = {}

        if metadata is None:
            metadata = {}

        if not isinstance(data, dict):
            raise TypeError("data must be dict or None")

        if not isinstance(metadata, dict):
            raise TypeError("metadata must be dict or None")

        if error is not None and not isinstance(error, ProtocolError):
            raise TypeError("error must be ProtocolError or None")

        if success and error is not None:
            raise ValueError("successful response cannot contain error")

        if not success and error is None:
            raise ValueError("failed response requires error")

        self.request_id = request_id
        self.service = service
        self.success = success
        self.data = self._copy(data)
        self.error = error
        self.metadata = self._copy(metadata)
        self.correlation_id = correlation_id
        self.trace_id = trace_id

    def to_dict(self):
        return {
            "request_id": self.request_id,
            "service": self.service,
            "success": self.success,
            "data": self._copy(self.data),
            "error": (
                None
                if self.error is None
                else self.error.to_dict()
            ),
            "metadata": self._copy(self.metadata),
            "correlation_id": self.correlation_id,
            "trace_id": self.trace_id,
        }

    def to_message(self):
        payload = {
            "success": self.success,
            "data": self._copy(self.data),
            "error": (
                None
                if self.error is None
                else self.error.to_dict()
            ),
            "metadata": self._copy(self.metadata),
        }

        return ProtocolMessage(
            message_id=(
                self.request_id
                + ":response"
            ),
            message_type=(
                "response"
                if self.success
                else "error"
            ),
            service=self.service,
            payload=payload,
            correlation_id=(
                self.correlation_id
                if self.correlation_id is not None
                else self.request_id
            ),
            trace_id=self.trace_id,
        )

    @classmethod
    def from_message(cls, message):
        if not isinstance(message, ProtocolMessage):
            raise TypeError("message must be ProtocolMessage")

        if message.message_type not in (
            "response",
            "error",
        ):
            raise ValueError("message is not a response/error")

        body = message.payload
        error_value = body.get("error")

        error = (
            None
            if error_value is None
            else ProtocolError.from_dict(
                error_value
            )
        )

        request_id = (
            message.correlation_id
            if message.correlation_id is not None
            else message.message_id
        )

        return cls(
            request_id=request_id,
            service=message.service,
            success=bool(
                body["success"]
            ),
            data=body.get("data", {}),
            error=error,
            metadata=body.get("metadata", {}),
            correlation_id=message.correlation_id,
            trace_id=message.trace_id,
        )

    @classmethod
    def success_response(
        cls,
        request,
        data=None,
        metadata=None,
    ):
        if not isinstance(request, ServiceRequest):
            raise TypeError("request must be ServiceRequest")

        return cls(
            request_id=request.request_id,
            service=request.service,
            success=True,
            data=data,
            metadata=metadata,
            correlation_id=request.request_id,
            trace_id=request.trace_id,
        )

    @classmethod
    def error_response(
        cls,
        request,
        error,
        metadata=None,
    ):
        if not isinstance(request, ServiceRequest):
            raise TypeError("request must be ServiceRequest")

        return cls(
            request_id=request.request_id,
            service=request.service,
            success=False,
            error=error,
            metadata=metadata,
            correlation_id=request.request_id,
            trace_id=request.trace_id,
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
