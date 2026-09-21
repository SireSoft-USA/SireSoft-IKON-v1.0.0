class RuntimeMaintenanceManager:
    """
    Coordinates normal -> draining -> maintenance -> normal transitions.

    Draining prevents new ServiceHost work. Transition to maintenance occurs
    only after active requests reach zero.
    """

    def __init__(
        self,
        host,
        state=None,
        drain_manager=None,
    ):
        if not isinstance(
            host,
            ServiceHost,
        ):
            raise TypeError(
                "host must be ServiceHost"
            )

        self.host = host

        self.state = (
            MaintenanceState()
            if state is None
            else state
        )

        self.drain_manager = (
            ServiceDrainManager(
                host
            )
            if drain_manager is None
            else drain_manager
        )

        self.enter_count = 0
        self.exit_count = 0

    def begin_draining(
        self,
        now,
        reason="maintenance",
    ):
        if self.state.mode == "maintenance":
            raise RuntimeError(
                "runtime is already in maintenance"
            )

        if self.state.mode == "draining":
            return self.status()

        self.drain_manager.begin(
            now
        )

        self.state.transition(
            "draining",
            now,
            reason=reason,
        )

        return self.status()

    def advance(
        self,
        now,
    ):
        if self.state.mode != "draining":
            return self.status()

        if not self.drain_manager.drained():
            return self.status()

        self.state.transition(
            "maintenance",
            now,
            reason=self.state.reason,
        )

        self.enter_count += 1

        return self.status()

    def enter(
        self,
        now,
        reason="maintenance",
    ):
        self.begin_draining(
            now,
            reason=reason,
        )

        return self.advance(
            now
        )

    def exit(
        self,
        now,
    ):
        if self.state.mode == "normal":
            return self.status()

        if self.state.mode == "draining":
            if not self.drain_manager.drained():
                raise RuntimeError(
                    "cannot exit while active requests are still draining"
                )

        self.drain_manager.restore()

        self.state.transition(
            "normal",
            now,
            reason=None,
        )

        self.exit_count += 1

        return self.status()

    def status(
        self,
    ):
        drain = (
            self.drain_manager
            .status()
        )

        return {
            "mode": (
                self.state.mode
            ),
            "reason": (
                self.state.reason
            ),
            "accepting_requests": (
                self.state
                .accepting_requests()
            ),
            "drain": drain,
            "enter_count": (
                self.enter_count
            ),
            "exit_count": (
                self.exit_count
            ),
            "state": (
                self.state.to_dict()
            ),
        }
