class TracingService:
    """
    Protocol-facing tracing service.

    Supported operations:
      start_span
      finish_span
      add_event
      set_attribute
      get_trace
      list_traces
      save_state
      load_state
      status
    """

    def __init__(
        self,
        manager=None,
    ):
        self.manager = (
            TracingManager()
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
            "tracing_service"
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

            if operation == "start_span":
                result = (
                    self.manager
                    .start_span(
                        trace_id=self._required(
                            request.payload,
                            "trace_id",
                        ),
                        name=self._required(
                            request.payload,
                            "name",
                        ),
                        service_name=self._required(
                            request.payload,
                            "service_name",
                        ),
                        start_time=self._required(
                            request.payload,
                            "start_time",
                        ),
                        parent_span_id=request.payload.get(
                            "parent_span_id"
                        ),
                        operation=request.payload.get(
                            "operation"
                        ),
                        correlation_id=request.payload.get(
                            "correlation_id",
                            request.correlation_id,
                        ),
                        attributes=request.payload.get(
                            "attributes"
                        ),
                        trace_metadata=request.payload.get(
                            "trace_metadata"
                        ),
                    )
                )

                return self._success(
                    request,
                    {
                        "trace": result,
                    },
                )

            if operation == "finish_span":
                result = (
                    self.manager
                    .finish_span(
                        trace_id=self._required(
                            request.payload,
                            "trace_id",
                        ),
                        span_id=self._required(
                            request.payload,
                            "span_id",
                        ),
                        end_time=self._required(
                            request.payload,
                            "end_time",
                        ),
                        status=request.payload.get(
                            "status",
                            "ok",
                        ),
                        error_type=request.payload.get(
                            "error_type"
                        ),
                        error_message=request.payload.get(
                            "error_message"
                        ),
                    )
                )

                return self._success(
                    request,
                    {
                        "trace": result,
                    },
                )

            if operation == "add_event":
                span = (
                    self.manager
                    .add_event(
                        trace_id=self._required(
                            request.payload,
                            "trace_id",
                        ),
                        span_id=self._required(
                            request.payload,
                            "span_id",
                        ),
                        name=self._required(
                            request.payload,
                            "name",
                        ),
                        timestamp=self._required(
                            request.payload,
                            "timestamp",
                        ),
                        attributes=request.payload.get(
                            "attributes"
                        ),
                    )
                )

                return self._success(
                    request,
                    {
                        "span": span,
                    },
                )

            if operation == "set_attribute":
                span = (
                    self.manager
                    .set_attribute(
                        trace_id=self._required(
                            request.payload,
                            "trace_id",
                        ),
                        span_id=self._required(
                            request.payload,
                            "span_id",
                        ),
                        key=self._required(
                            request.payload,
                            "key",
                        ),
                        value=self._required(
                            request.payload,
                            "value",
                        ),
                    )
                )

                return self._success(
                    request,
                    {
                        "span": span,
                    },
                )

            if operation == "get_trace":
                trace = (
                    self.manager
                    .get_trace(
                        self._required(
                            request.payload,
                            "trace_id",
                        )
                    )
                )

                return self._success(
                    request,
                    {
                        "trace": (
                            trace.public_dict()
                        ),
                    },
                )

            if operation == "list_traces":
                traces = (
                    self.manager
                    .list_traces(
                        sampled=request.payload.get(
                            "sampled"
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
                )

                return self._success(
                    request,
                    {
                        "traces": traces,
                        "count": len(
                            traces
                        ),
                    },
                )

            if operation == "save_state":
                info = (
                    self.manager
                    .save_state(
                        self._required(
                            request.payload,
                            "path",
                        )
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
                    "Unsupported tracing service operation"
                ),
            )

        except KeyError as error:
            return self._error(
                request,
                "NOT_FOUND",
                str(
                    error
                ),
            )

        except RuntimeError as error:
            return self._error(
                request,
                "CONFLICT",
                str(
                    error
                ),
            )

        except FileNotFoundError as error:
            return self._error(
                request,
                "NOT_FOUND",
                str(
                    error
                ),
            )

        except (
            ValueError,
            TypeError,
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
