class RuntimeMonitoringBridge:
    """
    Produces MonitoringService-compatible health payloads without duplicating
    runtime probe logic.
    """

    def __init__(
        self,
        health_manager,
    ):
        if not isinstance(
            health_manager,
            RuntimeHealthManager,
        ):
            raise TypeError(
                "health_manager must be RuntimeHealthManager"
            )

        self.health_manager = (
            health_manager
        )

    def health(
        self,
    ):
        runtime = (
            self.health_manager
            .check()
        )

        return {
            "status": (
                runtime[
                    "status"
                ]
            ),
            "ready": (
                runtime[
                    "ready"
                ]
            ),
            "live": (
                runtime[
                    "live"
                ]
            ),
            "runtime": (
                runtime
            ),
        }
