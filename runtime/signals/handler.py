import signal


class RuntimeSignalHandler:
    """
    Installs lightweight process-signal handlers.

    The signal handler records intent only. Actual lifecycle teardown stays
    outside the handler and runs through RuntimeShutdownBridge.
    """

    def __init__(
        self,
        coordinator,
        registry=None,
    ):
        if not isinstance(
            coordinator,
            ShutdownCoordinator,
        ):
            raise TypeError(
                "coordinator must be ShutdownCoordinator"
            )

        self.coordinator = coordinator

        self.registry = (
            RuntimeSignalRegistry()
            if registry is None
            else registry
        )

        self._installed = False
        self._previous = {}

        self.install_count = 0
        self.restore_count = 0

    def install(
        self,
    ):
        if self._installed:
            return self

        staged = []

        try:
            for item in self.registry.items():
                number = item[
                    "number"
                ]

                previous = signal.getsignal(
                    number
                )

                signal.signal(
                    number,
                    self._handle,
                )

                self._previous[
                    number
                ] = previous

                staged.append(
                    number
                )

        except BaseException:
            index = len(
                staged
            ) - 1

            while index >= 0:
                number = staged[
                    index
                ]

                signal.signal(
                    number,
                    self._previous[
                        number
                    ],
                )

                index -= 1

            self._previous = {}

            raise

        self._installed = True
        self.install_count += 1

        return self

    def restore(
        self,
    ):
        if not self._installed:
            return self

        items = self.registry.items()
        index = len(
            items
        ) - 1

        while index >= 0:
            number = items[
                index
            ][
                "number"
            ]

            if number in self._previous:
                signal.signal(
                    number,
                    self._previous[
                        number
                    ],
                )

            index -= 1

        self._previous = {}
        self._installed = False
        self.restore_count += 1

        return self

    def installed(
        self,
    ):
        return self._installed

    def simulate(
        self,
        signal_number,
    ):
        if not isinstance(
            signal_number,
            int,
        ):
            raise TypeError(
                "signal_number must be int"
            )

        self._handle(
            signal_number,
            None,
        )

        return self.coordinator.event()

    def status(
        self,
    ):
        return {
            "installed": (
                self._installed
            ),
            "install_count": (
                self.install_count
            ),
            "restore_count": (
                self.restore_count
            ),
            "signals": (
                self.registry.items()
            ),
            "coordinator": (
                self.coordinator
                .status()
            ),
        }

    def _handle(
        self,
        signal_number,
        frame,
    ):
        name = self.registry.name_for(
            int(
                signal_number
            )
        )

        self.coordinator.request(
            reason=(
                "process signal "
                + name
            ),
            signal_name=name,
            signal_number=int(
                signal_number
            ),
        )
