class ProcessGroup:
    """
    Ordered group lifecycle for related SireLLM child processes.

    Start order is registration order. Stop order is reversed so dependencies
    can be torn down after their consumers.
    """

    def __init__(
        self,
        supervisor,
        names,
    ):
        if not isinstance(
            supervisor,
            ProcessSupervisor,
        ):
            raise TypeError(
                "supervisor must be ProcessSupervisor"
            )

        if not isinstance(
            names,
            (list, tuple),
        ) or len(
            names
        ) == 0:
            raise ValueError(
                "names must be non-empty list/tuple"
            )

        normalized = []

        for name in names:
            if not isinstance(
                name,
                str,
            ) or name == "":
                raise ValueError(
                    "group process names must be non-empty strings"
                )

            supervisor.registry.get_spec(
                name
            )

            if name in normalized:
                raise ValueError(
                    "duplicate process name in group"
                )

            normalized.append(
                name
            )

        self.supervisor = (
            supervisor
        )
        self.names = normalized

    def start_all(
        self,
    ):
        started = []

        try:
            for name in self.names:
                self.supervisor.start(
                    name
                )

                started.append(
                    name
                )

        except Exception:
            index = (
                len(
                    started
                )
                - 1
            )

            while index >= 0:
                self.supervisor.stop(
                    started[
                        index
                    ]
                )
                index -= 1

            raise

        return started

    def stop_all(
        self,
        timeout=None,
    ):
        stopped = []

        index = (
            len(
                self.names
            )
            - 1
        )

        while index >= 0:
            name = self.names[
                index
            ]

            self.supervisor.stop(
                name,
                timeout=timeout,
            )

            stopped.append(
                name
            )

            index -= 1

        return stopped
