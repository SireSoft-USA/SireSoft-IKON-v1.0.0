class ProtocolValidator:
    """
    Structural validator for internal protocol objects and message payloads.
    """

    SUPPORTED_VERSION = "1.0"

    def validate_message(self, message):
        errors = []

        if not isinstance(message, ProtocolMessage):
            return [
                "object is not ProtocolMessage"
            ]

        if message.protocol_version != self.SUPPORTED_VERSION:
            errors.append(
                "unsupported protocol_version"
            )

        if message.message_type == "request":
            if "operation" not in message.payload:
                errors.append(
                    "request payload missing operation"
                )

            if "payload" not in message.payload:
                errors.append(
                    "request payload missing payload"
                )

        elif message.message_type in (
            "response",
            "error",
        ):
            if "success" not in message.payload:
                errors.append(
                    "response payload missing success"
                )

            if "data" not in message.payload:
                errors.append(
                    "response payload missing data"
                )

            if "error" not in message.payload:
                errors.append(
                    "response payload missing error"
                )

        return errors

    def require_valid_message(self, message):
        errors = self.validate_message(
            message
        )

        if len(errors) > 0:
            raise ValueError(
                "invalid protocol message: "
                + "; ".join(errors)
            )

        return message

    def validate_request(self, request):
        if not isinstance(request, ServiceRequest):
            return [
                "object is not ServiceRequest"
            ]

        errors = []

        if request.operation.strip() == "":
            errors.append(
                "operation must not be blank"
            )

        return errors

    def validate_response(self, response):
        if not isinstance(response, ServiceResponse):
            return [
                "object is not ServiceResponse"
            ]

        errors = []

        if response.success and response.error is not None:
            errors.append(
                "successful response contains error"
            )

        if not response.success and response.error is None:
            errors.append(
                "failed response missing error"
            )

        return errors
