class LifecycleManager:
    """
    Coordinates deterministic runtime startup and reverse-order shutdown.

    Startup is transactional at the lifecycle level: if any resource fails to
    start, every resource successfully started during that call is stopped in
    reverse order.
    """

    PHASES = (
        "created",
        "starting",
        "running",
        "stopping",
        "stopped",
        "failed",
    )

    def __init__(
        self,
        graph=None,
    ):
        self.graph = (
            LifecycleGraph()
            if graph is None
            else graph
        )

        self.phase = "created"
        self.last_error = None
        self.last_start_order = []
        self.last_stop_order = []

        self.total_start_cycles = 0
        self.total_stop_cycles = 0
        self.total_rollbacks = 0

    def register(
        self,
        resource,
    ):
        if self.phase in (
            "starting",
            "stopping",
        ):
            raise RuntimeError(
                "cannot register resources during lifecycle transition"
            )

        return self.graph.add(
            resource
        )

    def start_all(
        self,
    ):
        if self.phase == "running":
            return list(
                self.last_start_order
            )

        if self.phase in (
            "starting",
            "stopping",
        ):
            raise RuntimeError(
                "lifecycle transition already in progress"
            )

        order = self.graph.resolve_order()

        self.phase = "starting"
        self.last_error = None
        self.last_start_order = []

        started = []

        try:
            for name in order:
                resource = self.graph.get(
                    name
                )

                # Dependencies must already be running.
                for dependency in resource.dependencies:
                    dependency_resource = (
                        self.graph.get(
                            dependency
                        )
                    )

                    if dependency_resource.state != "running":
                        raise RuntimeError(
                            "dependency is not running: "
                            + dependency
                        )

                resource.start()

                started.append(
                    name
                )

            self.last_start_order = list(
                started
            )

            self.total_start_cycles += 1
            self.phase = "running"

            return list(
                started
            )

        except BaseException as error:
            self.last_error = str(
                error
            )

            rollback_order = list(
                started
            )
            rollback_order.reverse()

            for name in rollback_order:
                try:
                    self.graph.get(
                        name
                    ).stop()
                except BaseException:
                    # Preserve the original startup error.
                    pass

            self.last_stop_order = (
                rollback_order
            )

            if len(
                started
            ) > 0:
                self.total_rollbacks += 1

            self.phase = "failed"
            raise

    def stop_all(
        self,
    ):
        if self.phase == "stopped":
            return list(
                self.last_stop_order
            )

        if self.phase in (
            "starting",
            "stopping",
        ):
            raise RuntimeError(
                "lifecycle transition already in progress"
            )

        self.phase = "stopping"
        self.last_error = None

        order = self.graph.reverse_order()

        stopped = []
        errors = []

        for name in order:
            resource = self.graph.get(
                name
            )

            if resource.state not in (
                "running",
                "failed",
            ):
                continue

            try:
                resource.stop()

                stopped.append(
                    name
                )

            except BaseException as error:
                errors.append(
                    (
                        name,
                        str(
                            error
                        ),
                    )
                )

        self.last_stop_order = list(
            stopped
        )

        self.total_stop_cycles += 1

        if len(errors) > 0:
            self.phase = "failed"
            self.last_error = repr(
                errors
            )

            raise RuntimeError(
                "one or more lifecycle resources failed to stop"
            )

        self.phase = "stopped"

        return list(
            stopped
        )

    def resource_status(
        self,
        name,
    ):
        return self.graph.get(
            name
        ).status()

    def status(
        self,
    ):
        resources = [
            self.graph.get(
                name
            ).status()
            for name
            in self.graph.names()
        ]

        running = 0
        failed = 0

        for row in resources:
            if row[
                "state"
            ] == "running":
                running += 1

            if row[
                "state"
            ] == "failed":
                failed += 1

        return {
            "phase": self.phase,
            "ready": (
                self.phase
                == "running"
                and failed == 0
            ),
            "resource_count": len(
                resources
            ),
            "running_resources": (
                running
            ),
            "failed_resources": (
                failed
            ),
            "resources": resources,
            "last_start_order": list(
                self.last_start_order
            ),
            "last_stop_order": list(
                self.last_stop_order
            ),
            "last_error": (
                self.last_error
            ),
            "total_start_cycles": (
                self.total_start_cycles
            ),
            "total_stop_cycles": (
                self.total_stop_cycles
            ),
            "total_rollbacks": (
                self.total_rollbacks
            ),
        }
