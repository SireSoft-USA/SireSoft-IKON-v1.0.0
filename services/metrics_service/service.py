class MetricsService:
    """
    Protocol-facing metrics service.

    Supported operations:
      define
      increment
      set_gauge
      observe
      get_metric
      list_definitions
      snapshot
      save_state
      load_state
      status
    """

    def __init__(
        self,
        manager=None,
    ):
        self.manager = (
            MetricsManager()
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
            "metrics_service"
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

            if operation == "define":
                definition = (
                    self.manager
                    .define(
                        name=self._required(
                            request.payload,
                            "name",
                        ),
                        metric_type=self._required(
                            request.payload,
                            "metric_type",
                        ),
                        description=request.payload.get(
                            "description",
                            "",
                        ),
                        unit=request.payload.get(
                            "unit"
                        ),
                        label_names=request.payload.get(
                            "label_names"
                        ),
                        buckets=request.payload.get(
                            "buckets"
                        ),
                    )
                )

                return self._success(
                    request,
                    {
                        "definition": (
                            definition
                            .public_dict()
                        ),
                    },
                )

            if operation == "increment":
                result = (
                    self.manager
                    .increment(
                        name=self._required(
                            request.payload,
                            "name",
                        ),
                        timestamp=self._required(
                            request.payload,
                            "timestamp",
                        ),
                        amount=request.payload.get(
                            "amount",
                            1,
                        ),
                        labels=request.payload.get(
                            "labels"
                        ),
                    )
                )

                return self._success(
                    request,
                    {
                        "metric": result,
                    },
                )

            if operation == "set_gauge":
                result = (
                    self.manager
                    .set_gauge(
                        name=self._required(
                            request.payload,
                            "name",
                        ),
                        value=self._required(
                            request.payload,
                            "value",
                        ),
                        timestamp=self._required(
                            request.payload,
                            "timestamp",
                        ),
                        labels=request.payload.get(
                            "labels"
                        ),
                    )
                )

                return self._success(
                    request,
                    {
                        "metric": result,
                    },
                )

            if operation == "observe":
                result = (
                    self.manager
                    .observe(
                        name=self._required(
                            request.payload,
                            "name",
                        ),
                        value=self._required(
                            request.payload,
                            "value",
                        ),
                        timestamp=self._required(
                            request.payload,
                            "timestamp",
                        ),
                        labels=request.payload.get(
                            "labels"
                        ),
                    )
                )

                return self._success(
                    request,
                    {
                        "metric": result,
                    },
                )

            if operation == "get_metric":
                return self._success(
                    request,
                    {
                        "metric": (
                            self.manager
                            .get_metric(
                                self._required(
                                    request.payload,
                                    "name",
                                )
                            )
                        ),
                    },
                )

            if operation == "list_definitions":
                definitions = (
                    self.manager
                    .registry
                    .list_definitions()
                )

                return self._success(
                    request,
                    {
                        "definitions": (
                            definitions
                        ),
                        "count": len(
                            definitions
                        ),
                    },
                )

            if operation == "snapshot":
                return self._success(
                    request,
                    {
                        "snapshot": (
                            self.manager
                            .snapshot()
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
                    "Unsupported metrics service operation"
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
