class RuntimeDaemon:
    """
    Production-style blocking runtime daemon.

    It owns server startup, the cooperative serve loop, and guaranteed stop.
    """

    def __init__(
        self,
        server,
        loop=None,
    ):
        if not isinstance(
            server,
            RuntimeHTTPApplicationServer,
        ):
            raise TypeError(
                "server must be RuntimeHTTPApplicationServer"
            )

        self.server = server

        self.loop = (
            RuntimeServeLoop(
                server
            )
            if loop is None
            else loop
        )

        if not isinstance(
            self.loop,
            RuntimeServeLoop,
        ):
            raise TypeError(
                "loop must be RuntimeServeLoop"
            )

        self.run_count = 0
        self.last_result = None

    def run(
        self,
    ):
        self.run_count += 1

        started = False

        try:
            self.server.start()
            started = True

            loop_status = (
                self.loop.run()
            )

            self.last_result = {
                "ok": (
                    loop_status[
                        "exit_reason"
                    ]
                    != "server_error"
                ),
                "started": True,
                "stopped": False,
                "loop": loop_status,
            }

        except BaseException as error:
            self.last_result = {
                "ok": False,
                "started": started,
                "stopped": False,
                "error": {
                    "type": (
                        type(
                            error
                        ).__name__
                    ),
                    "message": str(
                        error
                    ),
                },
                "loop": (
                    self.loop.status()
                ),
            }

        finally:
            if self.server.running:
                try:
                    self.server.stop()

                except BaseException as error:
                    if self.last_result is None:
                        self.last_result = {
                            "ok": False,
                            "started": started,
                            "stopped": False,
                            "loop": (
                                self.loop.status()
                            ),
                        }

                    self.last_result[
                        "ok"
                    ] = False

                    self.last_result[
                        "stop_error"
                    ] = {
                        "type": (
                            type(
                                error
                            ).__name__
                        ),
                        "message": str(
                            error
                        ),
                    }

            if self.last_result is None:
                self.last_result = {
                    "ok": True,
                    "started": started,
                    "loop": (
                        self.loop.status()
                    ),
                }

            self.last_result[
                "stopped"
            ] = not self.server.running

        return dict(
            self.last_result
        )

    def request_shutdown(
        self,
        reason,
        metadata=None,
    ):
        coordinator = (
            self.server.system
            .components
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
            "last_result": (
                None
                if self.last_result
                is None
                else dict(
                    self.last_result
                )
            ),
            "loop": (
                self.loop.status()
            ),
            "server": (
                self.server.status()
            ),
        }
