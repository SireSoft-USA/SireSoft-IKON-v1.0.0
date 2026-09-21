class RuntimeServerConfig:
    """
    HTTP exposure configuration for a composed RuntimeSystem.
    """

    def __init__(
        self,
        host="127.0.0.1",
        port=0,
        routes=None,
        middleware=None,
        context_enricher=None,
        backlog=64,
        timeout_seconds=5.0,
        recv_chunk_bytes=4096,
    ):
        if not isinstance(
            host,
            str,
        ) or host == "":
            raise ValueError(
                "host must be non-empty str"
            )

        if (
            not isinstance(
                port,
                int,
            )
            or port < 0
            or port > 65535
        ):
            raise ValueError(
                "port must be int 0..65535"
            )

        if routes is None:
            routes = []

        if not isinstance(
            routes,
            (list, tuple),
        ):
            raise TypeError(
                "routes must be list/tuple or None"
            )

        normalized_routes = []
        route_keys = {}

        for route in routes:
            if not isinstance(
                route,
                GatewayRoute,
            ):
                raise TypeError(
                    "routes entries must be GatewayRoute"
                )

            key = route.key()

            if key in route_keys:
                raise ValueError(
                    "duplicate server route: "
                    + key
                )

            route_keys[
                key
            ] = True

            normalized_routes.append(
                route
            )

        if middleware is not None and not isinstance(
            middleware,
            (list, tuple),
        ):
            raise TypeError(
                "middleware must be list/tuple or None"
            )

        if (
            context_enricher is not None
            and not callable(
                context_enricher
            )
        ):
            raise TypeError(
                "context_enricher must be callable or None"
            )

        if (
            not isinstance(
                backlog,
                int,
            )
            or backlog <= 0
        ):
            raise ValueError(
                "backlog must be positive int"
            )

        if (
            not isinstance(
                timeout_seconds,
                (int, float),
            )
            or timeout_seconds <= 0
        ):
            raise ValueError(
                "timeout_seconds must be positive"
            )

        if (
            not isinstance(
                recv_chunk_bytes,
                int,
            )
            or recv_chunk_bytes <= 0
        ):
            raise ValueError(
                "recv_chunk_bytes must be positive int"
            )

        self.host = host
        self.port = port
        self.routes = normalized_routes

        self.middleware = (
            None
            if middleware is None
            else list(
                middleware
            )
        )

        self.context_enricher = (
            context_enricher
        )

        self.backlog = backlog
        self.timeout_seconds = float(
            timeout_seconds
        )
        self.recv_chunk_bytes = (
            recv_chunk_bytes
        )

    def public_dict(
        self,
    ):
        return {
            "host": self.host,
            "port": self.port,
            "routes": [
                route.to_dict()
                for route
                in self.routes
            ],
            "middleware_count": (
                None
                if self.middleware
                is None
                else len(
                    self.middleware
                )
            ),
            "has_context_enricher": (
                self.context_enricher
                is not None
            ),
            "backlog": self.backlog,
            "timeout_seconds": (
                self.timeout_seconds
            ),
            "recv_chunk_bytes": (
                self.recv_chunk_bytes
            ),
        }
