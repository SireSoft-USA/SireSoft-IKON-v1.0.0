class LoggingService:
    """
    Protocol-facing structured logging service.

    Supported operations:
      log
      debug
      info
      warning
      error
      critical
      query
      set_minimum_level
      clear
      save_archive
      load_archive
      status
    """

    def __init__(
        self,
        manager=None,
    ):
        self.manager = (
            LoggingManager()
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
            "logging_service"
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

            if operation in (
                "log",
                "debug",
                "info",
                "warning",
                "error",
                "critical",
            ):
                if operation == "log":
                    level = self._required(
                        request.payload,
                        "level",
                    )
                else:
                    level = operation.upper()

                result = self.manager.log(
                    level=level,
                    message=self._required(
                        request.payload,
                        "message",
                    ),
                    timestamp=self._required(
                        request.payload,
                        "timestamp",
                    ),
                    service=request.payload.get(
                        "service"
                    ),
                    event=request.payload.get(
                        "event"
                    ),
                    trace_id=request.payload.get(
                        "trace_id",
                        request.trace_id,
                    ),
                    correlation_id=request.payload.get(
                        "correlation_id",
                        request.correlation_id,
                    ),
                    fields=request.payload.get(
                        "fields"
                    ),
                )

                return self._success(
                    request,
                    {
                        "log": result,
                    },
                )

            if operation == "query":
                result = self.manager.query(
                    minimum_level=request.payload.get(
                        "minimum_level"
                    ),
                    levels=request.payload.get(
                        "levels"
                    ),
                    service=request.payload.get(
                        "service"
                    ),
                    event=request.payload.get(
                        "event"
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

            if operation == "set_minimum_level":
                level = (
                    self.manager
                    .set_minimum_level(
                        self._required(
                            request.payload,
                            "level",
                        )
                    )
                )

                return self._success(
                    request,
                    {
                        "minimum_level": (
                            level
                        ),
                    },
                )

            if operation == "clear":
                return self._success(
                    request,
                    self.manager.clear(),
                )

            if operation == "save_archive":
                info = (
                    self.manager
                    .save_archive(
                        self._required(
                            request.payload,
                            "path",
                        )
                    )
                )

                return self._success(
                    request,
                    {
                        "archive": info,
                    },
                )

            if operation == "load_archive":
                info = (
                    self.manager
                    .load_archive(
                        path=self._required(
                            request.payload,
                            "path",
                        ),
                        replace=request.payload.get(
                            "replace",
                            True,
                        ),
                    )
                )

                return self._success(
                    request,
                    info,
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
                    "Unsupported logging service operation"
                ),
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
            KeyError,
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
