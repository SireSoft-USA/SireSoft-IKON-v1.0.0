class LifecycleGraph:
    """
    Deterministic dependency graph with cycle detection.
    """

    def __init__(
        self,
    ):
        self._resources = {}
        self._order = []

    def add(
        self,
        resource,
    ):
        if not isinstance(
            resource,
            LifecycleResource,
        ):
            raise TypeError(
                "resource must be LifecycleResource"
            )

        if resource.name in self._resources:
            raise ValueError(
                "resource already registered: "
                + resource.name
            )

        self._resources[
            resource.name
        ] = resource

        self._order.append(
            resource.name
        )

        return resource

    def get(
        self,
        name,
    ):
        if name not in self._resources:
            raise KeyError(
                "lifecycle resource not found: "
                + str(
                    name
                )
            )

        return self._resources[
            name
        ]

    def names(
        self,
    ):
        return list(
            self._order
        )

    def validate(
        self,
    ):
        for name in self._order:
            resource = self._resources[
                name
            ]

            for dependency in resource.dependencies:
                if dependency not in self._resources:
                    raise ValueError(
                        "resource "
                        + name
                        + " depends on missing resource "
                        + dependency
                    )

        # resolve_order also performs cycle detection.
        self.resolve_order()

        return True

    def resolve_order(
        self,
    ):
        states = {}
        result = []

        for name in self._order:
            states[
                name
            ] = 0

        for name in self._order:
            if states[
                name
            ] == 0:
                self._visit(
                    name,
                    states,
                    result,
                )

        return result

    def reverse_order(
        self,
    ):
        result = self.resolve_order()

        result.reverse()

        return result

    def _visit(
        self,
        name,
        states,
        result,
    ):
        state = states[
            name
        ]

        if state == 2:
            return

        if state == 1:
            raise ValueError(
                "lifecycle dependency cycle detected at "
                + name
            )

        states[
            name
        ] = 1

        resource = self._resources[
            name
        ]

        for dependency in resource.dependencies:
            if dependency not in self._resources:
                raise ValueError(
                    "resource "
                    + name
                    + " depends on missing resource "
                    + dependency
                )

            self._visit(
                dependency,
                states,
                result,
            )

        states[
            name
        ] = 2

        if name not in result:
            result.append(
                name
            )
