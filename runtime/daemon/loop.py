class RuntimeServeLoop:
    """
    Cooperative accept loop over RuntimeHTTPApplicationServer.

    RawHTTPServer accept timeout acts as the wake-up interval. TimeoutError is
    treated as an idle poll, not a server failure.
    """

    def __init__(
        self,
        server,
        config=None,
    ):
        if not isinstance(
            server,
            RuntimeHTTPApplicationServer,
        ):
            raise TypeError(
                "server must be RuntimeHTTPApplicationServer"
            )

        self.server = server

        self.config = (
            RuntimeDaemonConfig()
            if config is None
            else config
        )

        if not isinstance(
            self.config,
            RuntimeDaemonConfig,
        ):
            raise TypeError(
                "config must be RuntimeDaemonConfig"
            )

        self.requests_served = 0
        self.idle_timeouts = 0
        self.server_errors = 0
        self.last_error = None
        self.exit_reason = None

    def run(
        self,
    ):
        if not self.server.running:
            raise RuntimeError(
                "runtime HTTP application server must be running"
            )

        coordinator = (
            self.server.system
            .components
            .get(
                "shutdown_coordinator"
            )
        )

        while True:
            if coordinator.requested():
                self.exit_reason = (
                    "shutdown_requested"
                )
                break

            if (
                self.config.max_requests
                is not None
                and self.requests_served
                >= self.config.max_requests
            ):
                self.exit_reason = (
                    "request_limit"
                )
                break

            if (
                self.config.max_idle_timeouts
                is not None
                and self.idle_timeouts
                >= self.config.max_idle_timeouts
            ):
                self.exit_reason = (
                    "idle_timeout_limit"
                )
                break

            try:
                self.server.serve_once()
                self.requests_served += 1

            except TimeoutError:
                self.idle_timeouts += 1
                continue

            except OSError as error:
                if not self.server.running:
                    self.exit_reason = (
                        "server_stopped"
                    )
                    break

                self.server_errors += 1
                self.last_error = str(
                    error
                )

                if (
                    self.config
                    .stop_on_server_error
                ):
                    self.exit_reason = (
                        "server_error"
                    )
                    break

            except BaseException as error:
                self.server_errors += 1
                self.last_error = str(
                    error
                )

                if (
                    self.config
                    .stop_on_server_error
                ):
                    self.exit_reason = (
                        "server_error"
                    )
                    break

        return self.status()

    def status(
        self,
    ):
        return {
            "requests_served": (
                self.requests_served
            ),
            "idle_timeouts": (
                self.idle_timeouts
            ),
            "server_errors": (
                self.server_errors
            ),
            "last_error": (
                self.last_error
            ),
            "exit_reason": (
                self.exit_reason
            ),
            "config": (
                self.config.to_dict()
            ),
        }
