class RuntimeHTTPApplicationServer:
    """
    Owns a RuntimeSystem plus the raw HTTP exposure layer.

    Startup is transactional:
      1. start RuntimeSystem
      2. bind/listen HTTP socket
      3. rollback RuntimeSystem if bind/listen fails

    Shutdown reverses this order: stop accepting HTTP first, then stop runtime.
    """

    def __init__(
        self,
        system,
        config,
        gateway_factory=None,
    ):
        if not isinstance(
            system,
            RuntimeSystem,
        ):
            raise TypeError(
                "system must be RuntimeSystem"
            )

        if not isinstance(
            config,
            RuntimeServerConfig,
        ):
            raise TypeError(
                "config must be RuntimeServerConfig"
            )

        self.system = system
        self.config = config

        self.gateway_factory = (
            RuntimeGatewayFactory()
            if gateway_factory
            is None
            else gateway_factory
        )

        self.gateway = (
            self.gateway_factory
            .build(
                system,
                config,
            )
        )

        self.adapter = HTTPGatewayAdapter(
            gateway=self.gateway,
            context_enricher=(
                config.context_enricher
            ),
        )

        self.http_server = RawHTTPServer(
            host=config.host,
            port=config.port,
            adapter=self.adapter,
            backlog=config.backlog,
            timeout_seconds=(
                config.timeout_seconds
            ),
            recv_chunk_bytes=(
                config.recv_chunk_bytes
            ),
        )

        self.running = False
        self.start_count = 0
        self.stop_count = 0
        self.serve_count = 0
        self.last_error = None

    def start(
        self,
    ):
        if self.running:
            return self.status()

        self.last_error = None

        try:
            self.system.start()

        except BaseException as error:
            self.last_error = str(
                error
            )
            raise

        try:
            self.http_server.start()

        except BaseException as error:
            self.last_error = str(
                error
            )

            try:
                self.system.stop()

            except BaseException:
                pass

            raise

        self.running = True
        self.start_count += 1

        return self.status()

    def serve_once(
        self,
    ):
        if not self.running:
            raise RuntimeError(
                "runtime HTTP application server is not running"
            )

        result = self.http_server.serve_once()
        self.serve_count += 1

        return result

    def serve(
        self,
        max_requests,
    ):
        if (
            not isinstance(
                max_requests,
                int,
            )
            or max_requests <= 0
        ):
            raise ValueError(
                "max_requests must be positive int"
            )

        results = []

        index = 0

        while index < max_requests:
            results.append(
                self.serve_once()
            )

            index += 1

        return results

    def stop(
        self,
    ):
        if not self.running:
            return self.status()

        errors = []

        try:
            self.http_server.stop()

        except BaseException as error:
            errors.append(
                "http: "
                + str(
                    error
                )
            )

        try:
            self.system.stop()

        except BaseException as error:
            errors.append(
                "runtime: "
                + str(
                    error
                )
            )

        self.running = False
        self.stop_count += 1

        if len(
            errors
        ) > 0:
            self.last_error = "; ".join(
                errors
            )

            raise RuntimeError(
                self.last_error
            )

        return self.status()

    def status(
        self,
    ):
        return {
            "running": (
                self.running
            ),
            "start_count": (
                self.start_count
            ),
            "stop_count": (
                self.stop_count
            ),
            "serve_count": (
                self.serve_count
            ),
            "last_error": (
                self.last_error
            ),
            "server": (
                self.http_server
                .status()
            ),
            "runtime": (
                self.system.status()
            ),
            "routes": [
                route.to_dict()
                for route
                in self.config.routes
            ],
        }
