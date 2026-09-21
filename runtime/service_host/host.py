class ServiceHost:
    """
    Local in-process service host.

    It binds configured service handlers into the existing ServiceDiscovery and
    LoadBalancer layers. APIGateway and other callers dispatch ServiceRequest
    through this host rather than calling service objects directly.
    """

    def __init__(
        self,
        load_balancer=None,
        discovery=None,
        bindings=None,
    ):
        self.load_balancer = (
            LoadBalancer()
            if load_balancer is None
            else load_balancer
        )

        if discovery is None:
            self.discovery = (
                ServiceDiscoveryManager(
                    load_balancer=(
                        self.load_balancer
                    )
                )
            )

        else:
            self.discovery = discovery

            if (
                self.discovery
                .load_balancer
                is None
            ):
                self.discovery.load_balancer = (
                    self.load_balancer
                )

            elif (
                self.discovery
                .load_balancer
                is not self.load_balancer
            ):
                raise ValueError(
                    "discovery and host must share the same load balancer"
                )

        self.bindings = (
            HostBindingRegistry()
            if bindings is None
            else bindings
        )

        self.running = False
        self.started_at = None
        self.start_count = 0
        self.stop_count = 0

        if bindings is not None:
            if not isinstance(
                bindings,
                HostBindingRegistry,
            ):
                raise TypeError(
                    "bindings must be HostBindingRegistry or None"
                )

    def add(
        self,
        binding,
    ):
        if self.running:
            raise RuntimeError(
                "cannot add binding while service host is running"
            )

        return self.bindings.add(
            binding
        )

    def add_service(
        self,
        instance_id,
        service_name,
        handler,
        endpoint=None,
        lease_seconds=60,
        metadata=None,
        max_consecutive_failures=3,
    ):
        return self.add(
            ServiceBinding(
                instance_id=(
                    instance_id
                ),
                service_name=(
                    service_name
                ),
                handler=handler,
                endpoint=endpoint,
                lease_seconds=(
                    lease_seconds
                ),
                metadata=metadata,
                max_consecutive_failures=(
                    max_consecutive_failures
                ),
            )
        )

    def start(
        self,
        now,
    ):
        self._validate_now(
            now
        )

        if self.running:
            return self.status(
                now
            )

        registered = []

        try:
            for binding in self.bindings.bindings():
                self.discovery.register_local(
                    instance_id=(
                        binding.instance_id
                    ),
                    service_name=(
                        binding.service_name
                    ),
                    handler=(
                        binding.handler
                    ),
                    now=now,
                    endpoint=(
                        binding.endpoint
                    ),
                    lease_seconds=(
                        binding.lease_seconds
                    ),
                    metadata=(
                        binding.metadata
                    ),
                    max_consecutive_failures=(
                        binding
                        .max_consecutive_failures
                    ),
                )

                registered.append(
                    binding.instance_id
                )

        except BaseException:
            index = (
                len(
                    registered
                )
                - 1
            )

            while index >= 0:
                try:
                    self.discovery.deregister(
                        registered[
                            index
                        ]
                    )
                except BaseException:
                    pass

                index -= 1

            raise

        self.running = True
        self.started_at = now
        self.start_count += 1

        return self.status(
            now
        )

    def stop(
        self,
    ):
        if not self.running:
            return {
                "stopped": False,
                "deregistered": [],
            }

        deregistered = []

        bindings = (
            self.bindings.bindings()
        )

        index = (
            len(
                bindings
            )
            - 1
        )

        while index >= 0:
            binding = bindings[
                index
            ]

            try:
                self.discovery.deregister(
                    binding.instance_id
                )

                deregistered.append(
                    binding.instance_id
                )

            except KeyError:
                pass

            index -= 1

        self.running = False
        self.stop_count += 1

        return {
            "stopped": True,
            "deregistered": (
                deregistered
            ),
        }

    def dispatch(
        self,
        request,
    ):
        if not isinstance(
            request,
            ServiceRequest,
        ):
            raise TypeError(
                "request must be ServiceRequest"
            )

        if not self.running:
            return (
                ServiceResponse
                .error_response(
                    request,
                    ProtocolError(
                        code=(
                            "SERVICE_HOST_NOT_RUNNING"
                        ),
                        message=(
                            "Local service host is not running"
                        ),
                        details={},
                        retryable=True,
                    ),
                )
            )

        return self.load_balancer.dispatch(
            request
        )

    def heartbeat(
        self,
        instance_id,
        now,
    ):
        if not self.running:
            raise RuntimeError(
                "service host is not running"
            )

        return self.discovery.heartbeat(
            instance_id,
            now,
        )

    def heartbeat_all(
        self,
        now,
    ):
        if not self.running:
            raise RuntimeError(
                "service host is not running"
            )

        self._validate_now(
            now
        )

        updated = []

        for binding in self.bindings.bindings():
            descriptor = (
                self.discovery
                .heartbeat(
                    binding.instance_id,
                    now,
                )
            )

            updated.append(
                descriptor.instance_id
            )

        return updated

    def sweep_stale(
        self,
        now,
    ):
        if not self.running:
            raise RuntimeError(
                "service host is not running"
            )

        return (
            self.discovery
            .sweep_stale(
                now
            )
        )

    def mark_healthy(
        self,
        instance_id,
    ):
        return (
            self.discovery
            .mark_healthy(
                instance_id
            )
        )

    def mark_unhealthy(
        self,
        instance_id,
    ):
        return (
            self.discovery
            .mark_unhealthy(
                instance_id
            )
        )

    def enable(
        self,
        instance_id,
    ):
        return (
            self.discovery
            .enable(
                instance_id
            )
        )

    def disable(
        self,
        instance_id,
    ):
        return (
            self.discovery
            .disable(
                instance_id
            )
        )

    def status(
        self,
        now=None,
    ):
        discovery_status = None

        if now is not None:
            self._validate_now(
                now
            )

            discovery_status = (
                self.discovery
                .status(
                    now
                )
            )

        return {
            "running": (
                self.running
            ),
            "started_at": (
                self.started_at
            ),
            "configured_bindings": (
                self.bindings
                .count()
            ),
            "services": (
                self.bindings
                .services()
            ),
            "start_count": (
                self.start_count
            ),
            "stop_count": (
                self.stop_count
            ),
            "discovery": (
                discovery_status
            ),
            "load_balancer": (
                self.load_balancer
                .health_snapshot()
            ),
        }

    def _validate_now(
        self,
        now,
    ):
        if not isinstance(
            now,
            int,
        ):
            raise TypeError(
                "now must be integer seconds"
            )

        if now < 0:
            raise ValueError(
                "now must be non-negative"
            )
