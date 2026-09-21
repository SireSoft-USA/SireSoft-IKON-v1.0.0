class RuntimeComponents:
    """
    Named component registry owned by the composition root.
    """

    def __init__(
        self,
    ):
        self._values = {}
        self._order = []
        self._sealed = False

    def add(
        self,
        name,
        value,
    ):
        if self._sealed:
            raise RuntimeError(
                "runtime components are sealed"
            )

        if not isinstance(
            name,
            str,
        ) or name == "":
            raise ValueError(
                "component name must be non-empty str"
            )

        if name in self._values:
            raise ValueError(
                "duplicate runtime component: "
                + name
            )

        self._values[
            name
        ] = value

        self._order.append(
            name
        )

        return value

    def get(
        self,
        name,
    ):
        if name not in self._values:
            raise KeyError(
                "runtime component not found: "
                + str(
                    name
                )
            )

        return self._values[
            name
        ]

    def has(
        self,
        name,
    ):
        return name in self._values

    def names(
        self,
    ):
        return list(
            self._order
        )

    def seal(
        self,
    ):
        self._sealed = True
        return self

    def summary(
        self,
    ):
        return {
            "sealed": (
                self._sealed
            ),
            "count": len(
                self._order
            ),
            "names": list(
                self._order
            ),
        }
