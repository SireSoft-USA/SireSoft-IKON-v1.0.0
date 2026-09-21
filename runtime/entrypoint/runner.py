class RuntimeEntrypoint:
    """
    Top-level lifecycle runner for a composed RuntimeSystem.

    The runner never invents shutdown reasons or force-kills runtime resources.
    It starts the composed system, waits on its ShutdownCoordinator, then uses
    the existing RuntimeShutdownBridge for ordered teardown.
    """

    def __init__(
        self,
        system,
    ):
        if not isinstance(
            system,
            RuntimeSystem,
        ):
            raise TypeError(
                "system must be RuntimeSystem"
            )

        self.system = system
        self.run_count = 0
        self.last_status = None

    def run(
        self,
        wait_timeout=None,
    ):
        if wait_timeout is not None and (
            not isinstance(
                wait_timeout,
                (int, float),
            )
            or wait_timeout < 0
        ):
            raise ValueError(
                "wait_timeout must be non-negative or None"
            )

        self.run_count += 1

        started = False

        try:
            self.system.start()
            started = True

        except BaseException as error:
            status = RuntimeExitStatus(
                code=(
                    RuntimeExitStatus
                    .EXIT_STARTUP_FAILED
                ),
                reason=(
                    "runtime startup failed"
                ),
                started=False,
                stopped=self._is_stopped(),
                details={
                    "error_type": (
                        type(
                            error
                        ).__name__
                    ),
                    "error": str(
                        error
                    ),
                },
            )

            self.last_status = status
            return status

        coordinator = (
            self.system.components
            .get(
                "shutdown_coordinator"
            )
        )

        try:
            requested = coordinator.wait(
                timeout=wait_timeout
            )

        except BaseException as error:
            status = self._failure_after_start(
                RuntimeExitStatus
                .EXIT_RUNTIME_FAILED,
                "runtime wait failed",
                error,
            )

            self.last_status = status
            return status

        if not requested:
            try:
                self.system.stop()

            except BaseException as error:
                status = RuntimeExitStatus(
                    code=(
                        RuntimeExitStatus
                        .EXIT_SHUTDOWN_FAILED
                    ),
                    reason=(
                        "runtime stop failed after wait timeout"
                    ),
                    started=started,
                    stopped=self._is_stopped(),
                    details={
                        "error_type": (
                            type(
                                error
                            ).__name__
                        ),
                        "error": str(
                            error
                        ),
                    },
                )

                self.last_status = status
                return status

            status = RuntimeExitStatus(
                code=(
                    RuntimeExitStatus
                    .EXIT_WAIT_TIMEOUT
                ),
                reason=(
                    "shutdown wait timed out"
                ),
                started=True,
                stopped=True,
            )

            self.last_status = status
            return status

        try:
            result = (
                self.system
                .run_shutdown_if_requested()
            )

        except BaseException as error:
            status = RuntimeExitStatus(
                code=(
                    RuntimeExitStatus
                    .EXIT_SHUTDOWN_FAILED
                ),
                reason=(
                    "runtime shutdown failed"
                ),
                started=True,
                stopped=self._is_stopped(),
                details={
                    "error_type": (
                        type(
                            error
                        ).__name__
                    ),
                    "error": str(
                        error
                    ),
                },
            )

            self.last_status = status
            return status

        if not result.get(
            "stopped",
            False,
        ):
            status = RuntimeExitStatus(
                code=(
                    RuntimeExitStatus
                    .EXIT_SHUTDOWN_FAILED
                ),
                reason=(
                    "shutdown bridge did not stop runtime"
                ),
                started=True,
                stopped=self._is_stopped(),
                details={
                    "bridge_result": (
                        result
                    ),
                },
            )

            self.last_status = status
            return status

        event = coordinator.event()

        status = RuntimeExitStatus(
            code=(
                RuntimeExitStatus
                .EXIT_OK
            ),
            reason=(
                "runtime shutdown completed"
            ),
            started=True,
            stopped=True,
            details={
                "shutdown_event": (
                    None
                    if event is None
                    else event.to_dict()
                ),
            },
        )

        self.last_status = status
        return status

    def request_shutdown(
        self,
        reason,
        metadata=None,
    ):
        coordinator = (
            self.system.components
            .get(
                "shutdown_coordinator"
            )
        )

        return coordinator.request(
            reason=reason,
            metadata=metadata,
        )

    def status(
        self,
    ):
        return {
            "run_count": (
                self.run_count
            ),
            "last_status": (
                None
                if self.last_status
                is None
                else self.last_status
                .to_dict()
            ),
            "system": (
                self.system.status()
            ),
        }

    def _failure_after_start(
        self,
        code,
        reason,
        error,
    ):
        stop_error = None

        try:
            self.system.stop()

        except BaseException as shutdown_error:
            stop_error = {
                "error_type": (
                    type(
                        shutdown_error
                    ).__name__
                ),
                "error": str(
                    shutdown_error
                ),
            }

        details = {
            "error_type": (
                type(
                    error
                ).__name__
            ),
            "error": str(
                error
            ),
        }

        if stop_error is not None:
            details[
                "stop_error"
            ] = stop_error

        return RuntimeExitStatus(
            code=code,
            reason=reason,
            started=True,
            stopped=self._is_stopped(),
            details=details,
        )

    def _is_stopped(
        self,
    ):
        try:
            return bool(
                self.system
                .components
                .get(
                    "application"
                )
                .status()[
                    "stopped"
                ]
            )

        except BaseException:
            return False
