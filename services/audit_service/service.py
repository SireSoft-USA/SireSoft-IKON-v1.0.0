class AuditService:
    """
    Protocol-facing append-only audit service.

    Supported operations:
      record
      get
      query
      verify
      save_state
      load_state
      status

    There is deliberately no delete/clear operation.
    """

    def __init__(
        self,
        manager=None,
    ):
        self.manager = (
            AuditManager()
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

        if request.service != (
            "audit_service"
        ):
            return self._error(
                request,
                "INVALID_REQUEST",
                "Request targeted the wrong service",
            )

        try:
            operation = (
                request.operation
            )

            if operation == "record":
                record = (
                    self.manager
                    .record(
                        timestamp=self._required(
                            request.payload,
                            "timestamp",
                        ),
                        actor_id=self._required(
                            request.payload,
                            "actor_id",
                        ),
                        actor_type=self._required(
                            request.payload,
                            "actor_type",
                        ),
                        action=self._required(
                            request.payload,
                            "action",
                        ),
                        resource=self._required(
                            request.payload,
                            "resource",
                        ),
                        outcome=request.payload.get(
                            "outcome",
                            "unknown",
                        ),
                        metadata=request.payload.get(
                            "metadata"
                        ),
                        trace_id=request.payload.get(
                            "trace_id",
                            request.trace_id,
                        ),
                        correlation_id=request.payload.get(
                            "correlation_id",
                            request.correlation_id,
                        ),
                        audit_id=request.payload.get(
                            "audit_id"
                        ),
                    )
                )

                return self._success(
                    request,
                    {
                        "audit": (
                            record.to_dict()
                        ),
                    },
                )

            if operation == "get":
                record = self.manager.get(
                    self._required(
                        request.payload,
                        "audit_id",
                    )
                )

                return self._success(
                    request,
                    {
                        "audit": (
                            record.to_dict()
                        ),
                    },
                )

            if operation == "query":
                result = self.manager.query(
                    actor_id=request.payload.get(
                        "actor_id"
                    ),
                    actor_type=request.payload.get(
                        "actor_type"
                    ),
                    action=request.payload.get(
                        "action"
                    ),
                    resource=request.payload.get(
                        "resource"
                    ),
                    outcome=request.payload.get(
                        "outcome"
                    ),
                    trace_id=request.payload.get(
                        "trace_id"
                    ),
                    correlation_id=request.payload.get(
                        "correlation_id"
                    ),
                    start_timestamp=request.payload.get(
                        "start_timestamp"
                    ),
                    end_timestamp=request.payload.get(
                        "end_timestamp"
                    ),
                    limit=request.payload.get(
                        "limit",
                        100,
                    ),
                    newest_first=request.payload.get(
                        "newest_first",
                        False,
                    ),
                )

                return self._success(
                    request,
                    {
                        "query": result,
                    },
                )

            if operation == "verify":
                return self._success(
                    request,
                    {
                        "integrity": (
                            self.manager
                            .verify()
                        ),
                    },
                )

            if operation == "save_state":
                info = self.manager.save_state(
                    self._required(
                        request.payload,
                        "path",
                    )
                )

                return self._success(
                    request,
                    {
                        "artifact": info,
                    },
                )

            if operation == "load_state":
                info = (
                    self.manager
                    .load_state_file(
                        self._required(
                            request.payload,
                            "path",
                        )
                    )
                )

                return self._success(
                    request,
                    {
                        "status": info,
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

            return self._error(
                request,
                "INVALID_REQUEST",
                (
                    "Unsupported audit service operation"
                ),
            )

        except KeyError as error:
            return self._error(
                request,
                "NOT_FOUND",
                str(error),
            )

        except FileNotFoundError as error:
            return self._error(
                request,
                "NOT_FOUND",
                str(error),
            )

        except (
            ValueError,
            TypeError,
            IndexError,
        ) as error:
            return self._error(
                request,
                "INVALID_REQUEST",
                str(error),
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
