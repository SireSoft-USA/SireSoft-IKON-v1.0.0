class RuntimeSystem:
    """
    High-level runtime facade produced by RuntimeCompositionBuilder.

    Runtime-control requests bypass maintenance traffic blocking so operators
    can inspect and exit maintenance mode. Ordinary service traffic is routed
    through maintenance and observability wrappers.
    """

    def __init__(
        self,
        components,
    ):
        if not isinstance(
            components,
            RuntimeComponents,
        ):
            raise TypeError(
                "components must be RuntimeComponents"
            )

        self.components = components
        self.start_count = 0
        self.stop_count = 0

    def start(
        self,
    ):
        application = (
            self.components
            .get(
                "application"
            )
        )

        result = application.start()

        self.start_count += 1

        return result

    def stop(
        self,
    ):
        application = (
            self.components
            .get(
                "application"
            )
        )

        result = application.stop()

        self.stop_count += 1

        return result

    def dispatch(
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

        if (
            request.service
            == RuntimeControlService.TARGET
        ):
            return (
                self.components
                .get(
                    "control_service"
                )
                .handle(
                    request
                )
            )

        return (
            self.components
            .get(
                "request_dispatcher"
            )(
                request
            )
        )

    def run_shutdown_if_requested(
        self,
    ):
        return (
            self.components
            .get(
                "shutdown_bridge"
            )
            .run_shutdown_if_requested()
        )

    def status(
        self,
    ):
        application = (
            self.components
            .get(
                "application"
            )
        )

        host = (
            self.components
            .get(
                "service_host"
            )
        )

        spec = (
            self.components
            .get(
                "spec"
            )
        )

        return {
            "running": (
                application.status()[
                    "running"
                ]
            ),
            "start_count": (
                self.start_count
            ),
            "stop_count": (
                self.stop_count
            ),
            "components": (
                self.components
                .summary()
            ),
            "spec": (
                spec.public_dict()
            ),
            "application": (
                application.status()
            ),
            "service_host": (
                host.status(
                    spec.now()
                )
            ),
            "maintenance": (
                self.components
                .get(
                    "maintenance"
                )
                .status()
            ),
            "health": (
                self.components
                .get(
                    "health"
                )
                .check()
            ),
            "shutdown": (
                self.components
                .get(
                    "shutdown_coordinator"
                )
                .status()
            ),
        }
