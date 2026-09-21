class EventBusService:
    """
    Protocol-facing event bus.

    Handler/callback registration cannot cross the protocol boundary; runtime
    code registers subscriptions directly on EventBusManager.

    Supported operations:
      publish
      list_subscriptions
      enable_subscription
      disable_subscription
      history
      clear_history
      status
    """

    def __init__(
        self,
        manager=None,
    ):
        self.manager = (
            EventBusManager()
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
            "event_bus"
        ):
            return self._error(
                request,
                "INVALID_REQUEST",
                "Request targeted the wrong service",
            )

        try:
            operation = request.operation

            if operation == "publish":
                result = self.manager.publish(
                    topic=self._required(
                        request.payload,
                        "topic",
                    ),
                    timestamp=self._required(
                        request.payload,
                        "timestamp",
                    ),
                    payload=request.payload.get(
                        "payload"
                    ),
                    metadata=request.payload.get(
                        "metadata"
                    ),
                    source_service=request.payload.get(
                        "source_service"
                    ),
                    trace_id=request.payload.get(
                        "trace_id",
                        request.trace_id,
                    ),
                    correlation_id=request.payload.get(
                        "correlation_id",
                        request.correlation_id,
                    ),
                )

                return self._success(
                    request,
                    {
                        "publish": result,
                    },
                )

            if operation == "list_subscriptions":
                subscriptions = (
                    self.manager
                    .list_subscriptions()
                )

                return self._success(
                    request,
                    {
                        "subscriptions": (
                            subscriptions
                        ),
                        "count": len(
                            subscriptions
                        ),
                    },
                )

            if operation in (
                "enable_subscription",
                "disable_subscription",
            ):
                method = (
                    self.manager
                    .enable_subscription
                    if operation
                    == "enable_subscription"
                    else self.manager
                    .disable_subscription
                )

                subscription = method(
                    self._required(
                        request.payload,
                        "subscription_id",
                    )
                )

                return self._success(
                    request,
                    {
                        "subscription": (
                            subscription.summary()
                        ),
                    },
                )

            if operation == "history":
                result = self.manager.history(
                    topic=request.payload.get(
                        "topic"
                    ),
                    minimum_sequence=request.payload.get(
                        "minimum_sequence"
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
                        "history": result,
                    },
                )

            if operation == "clear_history":
                return self._success(
                    request,
                    self.manager.clear_history(),
                )

            if operation == "status":
                return self._success(
                    request,
                    {
                        "status": (
                            self.manager.status()
                        ),
                    },
                )

            return self._error(
                request,
                "INVALID_REQUEST",
                "Unsupported event bus operation",
            )

        except KeyError as error:
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

        return payload[key]

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
