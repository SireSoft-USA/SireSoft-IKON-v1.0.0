class MaintenanceDispatcher:
    """
    Explicit protocol boundary for maintenance/drain rejection.

    This gives callers a stable error instead of depending on whatever
    no-instance error the load balancer might otherwise return.
    """

    def __init__(
        self,
        maintenance_manager,
        dispatcher,
    ):
        if not isinstance(
            maintenance_manager,
            RuntimeMaintenanceManager,
        ):
            raise TypeError(
                "maintenance_manager must be RuntimeMaintenanceManager"
            )

        if callable(
            dispatcher
        ):
            resolved = dispatcher

        elif (
            hasattr(
                dispatcher,
                "handle",
            )
            and callable(
                dispatcher.handle
            )
        ):
            resolved = (
                dispatcher.handle
            )

        else:
            raise TypeError(
                "dispatcher must be callable or expose handle()"
            )

        self.maintenance_manager = (
            maintenance_manager
        )
        self.dispatcher = resolved

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

        mode = (
            self.maintenance_manager
            .state
            .mode
        )

        if mode == "draining":
            return (
                ServiceResponse
                .error_response(
                    request,
                    ProtocolError(
                        code=(
                            "RUNTIME_DRAINING"
                        ),
                        message=(
                            "Runtime is draining and not accepting new requests"
                        ),
                        details={},
                        retryable=True,
                    ),
                )
            )

        if mode == "maintenance":
            return (
                ServiceResponse
                .error_response(
                    request,
                    ProtocolError(
                        code=(
                            "RUNTIME_MAINTENANCE"
                        ),
                        message=(
                            "Runtime is in maintenance mode"
                        ),
                        details={},
                        retryable=True,
                    ),
                )
            )

        response = self.dispatcher(
            request
        )

        if not isinstance(
            response,
            ServiceResponse,
        ):
            raise TypeError(
                "maintenance dispatcher must return ServiceResponse"
            )

        return response
