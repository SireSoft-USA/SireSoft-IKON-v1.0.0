class ProcessSupervisor:
    """
    Supervises registered child processes and restart policies.
    """

    def __init__(
        self,
        registry=None,
    ):
        self.registry = (
            ProcessRegistry()
            if registry is None
            else registry
        )

        self._restart_counts = {}

        self.total_starts = 0
        self.total_restarts = 0
        self.total_failures = 0

    def register(
        self,
        spec,
    ):
        self.registry.register(
            spec
        )

        self._restart_counts[
            spec.name
        ] = 0

        return spec

    def start(
        self,
        name,
    ):
        spec = self.registry.get_spec(
            name
        )

        current = (
            self.registry
            .get_process(
                name
            )
        )

        if (
            current is not None
            and current.running()
        ):
            raise RuntimeError(
                "process is already running: "
                + name
            )

        process = ManagedProcess(
            spec
        )

        process.start()

        self.registry.set_process(
            name,
            process,
        )

        self.total_starts += 1

        return process

    def stop(
        self,
        name,
        timeout=None,
    ):
        process = (
            self.registry
            .get_process(
                name
            )
        )

        if process is None:
            return None

        if process.result() is not None:
            return process.result()

        return process.terminate(
            timeout=timeout
        )

    def poll(
        self,
        restart=True,
    ):
        events = []

        for name in self.registry.names():
            process = (
                self.registry
                .get_process(
                    name
                )
            )

            if process is None:
                continue

            code = process.poll()

            if code is None:
                continue

            result = process.result()

            if result is None:
                result = process.wait()

            if code != 0:
                self.total_failures += 1

            spec = (
                self.registry
                .get_spec(
                    name
                )
            )

            restart_count = (
                self._restart_counts[
                    name
                ]
            )

            restarted = False

            if (
                restart
                and spec.should_restart(
                    code,
                    restart_count,
                )
            ):
                self._restart_counts[
                    name
                ] += 1

                self.total_restarts += 1

                self.start(
                    name
                )

                restarted = True

            events.append({
                "name": name,
                "exit_code": code,
                "restarted": (
                    restarted
                ),
                "restart_count": (
                    self._restart_counts[
                        name
                    ]
                ),
            })

        return events

    def wait(
        self,
        name,
        timeout=None,
        restart=False,
    ):
        process = (
            self.registry
            .get_process(
                name
            )
        )

        if process is None:
            raise RuntimeError(
                "process has not been started: "
                + name
            )

        result = process.wait(
            timeout=timeout
        )

        if result.exit_code != 0:
            self.total_failures += 1

        if restart:
            spec = (
                self.registry
                .get_spec(
                    name
                )
            )

            count = (
                self._restart_counts[
                    name
                ]
            )

            if spec.should_restart(
                result.exit_code,
                count,
            ):
                self._restart_counts[
                    name
                ] += 1

                self.total_restarts += 1

                self.start(
                    name
                )

        return result

    def shutdown_all(
        self,
        timeout=None,
    ):
        results = {}

        names = self.registry.names()

        index = (
            len(
                names
            )
            - 1
        )

        while index >= 0:
            name = names[
                index
            ]

            process = (
                self.registry
                .get_process(
                    name
                )
            )

            if process is not None:
                results[
                    name
                ] = self.stop(
                    name,
                    timeout=timeout,
                )

            index -= 1

        return results

    def status(
        self,
    ):
        return {
            "processes": (
                self.registry
                .list()
            ),
            "restart_counts": dict(
                self._restart_counts
            ),
            "total_starts": (
                self.total_starts
            ),
            "total_restarts": (
                self.total_restarts
            ),
            "total_failures": (
                self.total_failures
            ),
        }
