class RuntimeShutdownBridge:
    """
    Performs the real RuntimeApplication stop once a shutdown request exists.
    """

    def __init__(
        self,
        coordinator,
        runtime_application,
    ):
        if not isinstance(
            coordinator,
            ShutdownCoordinator,
        ):
            raise TypeError(
                "coordinator must be ShutdownCoordinator"
            )

        if not isinstance(
            runtime_application,
            RuntimeApplication,
        ):
            raise TypeError(
                "runtime_application must be RuntimeApplication"
            )

        self.coordinator = coordinator
        self.runtime_application = (
            runtime_application
        )

        self.shutdown_count = 0
        self.last_event = None

    def run_shutdown_if_requested(
        self,
    ):
        if not self.coordinator.requested():
            return {
                "requested": False,
                "stopped": False,
            }

        runtime_status = (
            self.runtime_application
            .status()
        )

        if runtime_status[
            "stopped"
        ]:
            event = (
                self.coordinator.event()
            )

            return {
                "requested": True,
                "stopped": True,
                "event": (
                    None
                    if event is None
                    else event.to_dict()
                ),
            }

        event = self.coordinator.event()

        result = (
            self.runtime_application
            .stop()
        )

        self.shutdown_count += 1
        self.last_event = event

        return {
            "requested": True,
            "stopped": (
                result[
                    "stopped"
                ]
            ),
            "event": (
                None
                if event is None
                else event.to_dict()
            ),
        }

    def status(
        self,
    ):
        return {
            "shutdown_count": (
                self.shutdown_count
            ),
            "last_event": (
                None
                if self.last_event
                is None
                else self.last_event
                .to_dict()
            ),
            "runtime": (
                self.runtime_application
                .status()
            ),
        }
