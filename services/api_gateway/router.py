class GatewayRouter:
    """
    Deterministic exact-route registry.

    Dynamic path parameters are intentionally deferred until the transport layer
    exists. This keeps service routing explicit and testable.
    """

    def __init__(self):
        self._routes = {}
        self._order = []

    def add(self, route):
        if not isinstance(route, GatewayRoute):
            raise TypeError("route must be GatewayRoute")

        key = route.key()

        if key in self._routes:
            raise ValueError(
                "duplicate gateway route: "
                + key
            )

        self._routes[key] = route
        self._order.append(key)
        return self

    def resolve(self, method, path):
        if not isinstance(method, str):
            raise TypeError("method must be str")

        if not isinstance(path, str):
            raise TypeError("path must be str")

        key = (
            method.upper()
            + " "
            + path
        )

        if key not in self._routes:
            return None

        return self._routes[key]

    def remove(self, method, path):
        route = self.resolve(
            method,
            path,
        )

        if route is None:
            raise KeyError(
                "gateway route not found"
            )

        key = route.key()
        del self._routes[key]

        new_order = []

        for existing in self._order:
            if existing != key:
                new_order.append(
                    existing
                )

        self._order = new_order
        return route

    def routes(self):
        return [
            self._routes[key]
            for key in self._order
        ]

    def count(self):
        return len(self._order)
