class GatewayConfigCatalog:
    """
    Deterministic route catalog keyed by METHOD + path.
    """

    def __init__(
        self,
    ):
        self._routes = {}
        self._order = []

    def add(
        self,
        route,
    ):
        if not isinstance(
            route,
            GatewayRouteConfig,
        ):
            raise TypeError(
                "route must be GatewayRouteConfig"
            )

        key = route.key()

        if key in self._routes:
            raise ValueError(
                "duplicate gateway route: "
                + key
            )

        self._routes[
            key
        ] = route

        self._order.append(
            key
        )

        return route

    def get(
        self,
        method,
        path,
    ):
        key = (
            str(
                method
            ).upper()
            + " "
            + str(
                path
            )
        )

        if key not in self._routes:
            raise KeyError(
                "gateway route not found: "
                + key
            )

        return self._routes[
            key
        ]

    def routes(
        self,
        enabled_only=False,
    ):
        output = []

        for key in self._order:
            route = self._routes[
                key
            ]

            if (
                enabled_only
                and not route.enabled
            ):
                continue

            output.append(
                route
            )

        return output

    def count(
        self,
        enabled_only=False,
    ):
        return len(
            self.routes(
                enabled_only=(
                    enabled_only
                )
            )
        )

    def to_dict(
        self,
    ):
        return {
            "route_count": self.count(),
            "enabled_route_count": (
                self.count(
                    enabled_only=True
                )
            ),
            "routes": [
                route.to_dict()
                for route
                in self.routes()
            ],
        }
