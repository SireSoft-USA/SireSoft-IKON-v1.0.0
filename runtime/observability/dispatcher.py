class ObservedDispatcher:
    """
    Wraps a synchronous ServiceRequest dispatcher with unified observability.
    """

    def __init__(
        self,
        observability,
        dispatcher,
        time_provider,
    ):
        if not isinstance(
            observability,
            RuntimeObservability,
        ):
            raise TypeError(
                "observability must be RuntimeObservability"
            )

        if callable(
            dispatcher
        ):
            self.dispatcher = dispatcher

        elif (
            hasattr(
                dispatcher,
                "handle",
            )
            and callable(
                dispatcher.handle
            )
        ):
            self.dispatcher = (
                dispatcher.handle
            )

        else:
            raise TypeError(
                "dispatcher must be callable or expose handle()"
            )

        if not callable(
            time_provider
        ):
            raise TypeError(
                "time_provider must be callable"
            )

        self.observability = observability
        self.time_provider = time_provider

    def __call__(
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

        context = self.observability.begin_request(
            request,
            self.time_provider(),
        )

        try:
            response = self.dispatcher(
                request
            )

            if not isinstance(
                response,
                ServiceResponse,
            ):
                raise TypeError(
                    "observed dispatcher must return ServiceResponse"
                )

            self.observability.finish_response(
                context,
                response,
                self.time_provider(),
            )

            return response

        except BaseException as error:
            if not context.finished:
                self.observability.finish_exception(
                    context,
                    error,
                    self.time_provider(),
                )

            raise
