class GuardrailService:
    """
    Protocol-facing safety/guardrail service.

    Supported operations:
      inspect_input
      inspect_context
      inspect_output
      policy_status
      status
      audit_summary
      clear_audit
    """

    def __init__(
        self,
        manager=None,
    ):
        self.manager = (
            GuardrailServiceManager()
            if manager is None
            else manager
        )

    def handle(
        self,
        request,
    ):
        if not isinstance(
            request,
            ServiceRequest,
        ):
            raise TypeError(
                "request must be ServiceRequest"
            )

        if request.service != "guardrail_service":
            return self._error(
                request,
                "INVALID_REQUEST",
                "Request targeted the wrong service",
            )

        try:
            operation = (
                request.operation
            )

            if operation == "inspect_input":
                result = (
                    self.manager
                    .inspect_input(
                        self._required(
                            request.payload,
                            "text",
                        ),
                        metadata=request.payload.get(
                            "metadata"
                        ),
                    )
                )

                return self._success(
                    request,
                    result,
                )

            if operation == "inspect_context":
                result = (
                    self.manager
                    .inspect_context(
                        self._required(
                            request.payload,
                            "text",
                        ),
                        metadata=request.payload.get(
                            "metadata"
                        ),
                    )
                )

                return self._success(
                    request,
                    result,
                )

            if operation == "inspect_output":
                result = (
                    self.manager
                    .inspect_output(
                        self._required(
                            request.payload,
                            "text",
                        ),
                        metadata=request.payload.get(
                            "metadata"
                        ),
                    )
                )

                return self._success(
                    request,
                    result,
                )

            if operation == "policy_status":
                return self._success(
                    request,
                    {
                        "policy": (
                            self.manager
                            .policy_status()
                        ),
                    },
                )

            if operation == "status":
                return self._success(
                    request,
                    {
                        "status": (
                            self.manager
                            .status()
                        ),
                    },
                )

            if operation == "audit_summary":
                records = (
                    self.manager
                    .audit_summary()
                )

                return self._success(
                    request,
                    {
                        "audit": records,
                        "count": len(
                            records
                        ),
                    },
                )

            if operation == "clear_audit":
                return self._success(
                    request,
                    self.manager
                    .clear_audit(),
                )

            return self._error(
                request,
                "INVALID_REQUEST",
                "Unsupported guardrail service operation",
            )

        except (
            ValueError,
            TypeError,
            KeyError,
            IndexError,
        ) as error:
            return self._error(
                request,
                "INVALID_REQUEST",
                str(
                    error
                ),
            )

    def _required(
        self,
        payload,
        key,
    ):
        if key not in payload:
            raise ValueError(
                "payload requires "
                + key
            )

        return payload[
            key
        ]

    def _success(
        self,
        request,
        data,
    ):
        return (
            ServiceResponse
            .success_response(
                request,
                data=data,
            )
        )

    def _error(
        self,
        request,
        code,
        message,
    ):
        return (
            ServiceResponse
            .error_response(
                request,
                ProtocolError(
                    code=code,
                    message=message,
                    retryable=False,
                ),
            )
        )
