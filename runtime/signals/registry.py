import signal


class RuntimeSignalRegistry:
    """
    Resolves the portable signal subset available on the current platform.
    """

    DEFAULT_NAMES = (
        "SIGINT",
        "SIGTERM",
    )

    def __init__(
        self,
        names=None,
    ):
        if names is None:
            names = self.DEFAULT_NAMES

        if not isinstance(
            names,
            (list, tuple),
        ):
            raise TypeError(
                "names must be list/tuple or None"
            )

        self._signals = {}
        self._order = []

        for name in names:
            self.add(
                name
            )

    def add(
        self,
        name,
    ):
        if not isinstance(
            name,
            str,
        ) or name == "":
            raise ValueError(
                "signal name must be non-empty str"
            )

        if name in self._signals:
            return self._signals[
                name
            ]

        if not hasattr(
            signal,
            name,
        ):
            return None

        number = int(
            getattr(
                signal,
                name,
            )
        )

        self._signals[
            name
        ] = number

        self._order.append(
            name
        )

        return number

    def number(
        self,
        name,
    ):
        if name not in self._signals:
            raise KeyError(
                "signal not registered or unavailable: "
                + str(
                    name
                )
            )

        return self._signals[
            name
        ]

    def name_for(
        self,
        number,
    ):
        if not isinstance(
            number,
            int,
        ):
            raise TypeError(
                "signal number must be int"
            )

        for name in self._order:
            if self._signals[
                name
            ] == number:
                return name

        return (
            "SIGNAL_"
            + str(
                number
            )
        )

    def items(
        self,
    ):
        return [
            {
                "name": name,
                "number": (
                    self._signals[
                        name
                    ]
                ),
            }
            for name in self._order
        ]

    def count(
        self,
    ):
        return len(
            self._order
        )
