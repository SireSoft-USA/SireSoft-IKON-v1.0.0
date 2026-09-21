class ServiceDiscoveryManager:
    """
    Lease-based service discovery with optional local LoadBalancer binding.

    Registration/discovery stays transport-neutral. Local runtime handlers can
    be bound directly so the existing internal LoadBalancer can dispatch to the
    same discovered instance.
    """

    def __init__(
        self,
        registry=None,
        load_balancer=None,
    ):
        self.registry = (
            DiscoveryRegistry()
            if registry is None
            else registry
        )

        self.load_balancer = (
            load_balancer
        )

        self._local_handlers = {}

    def register_instance(
        self,
        instance_id,
        service_name,
        endpoint,
        now,
        lease_seconds=60,
        metadata=None,
    ):
        descriptor = (
            ServiceDescriptor(
                instance_id=instance_id,
                service_name=(
                    service_name
                ),
                endpoint=endpoint,
                registered_at=now,
                lease_seconds=(
                    lease_seconds
                ),
                metadata=metadata,
            )
        )

        return self.registry.register(
            descriptor
        )

    def register_local(
        self,
        instance_id,
        service_name,
        handler,
        now,
        endpoint=None,
        lease_seconds=60,
        metadata=None,
        max_consecutive_failures=3,
    ):
        if not callable(
            handler
        ):
            raise TypeError(
                "handler must be callable"
            )

        if endpoint is None:
            endpoint = (
                "local://"
                + service_name
                + "/"
                + instance_id
            )

        descriptor = (
            self.register_instance(
                instance_id=instance_id,
                service_name=(
                    service_name
                ),
                endpoint=endpoint,
                now=now,
                lease_seconds=(
                    lease_seconds
                ),
                metadata=metadata,
            )
        )

        try:
            self.bind_local_handler(
                instance_id=instance_id,
                handler=handler,
                max_consecutive_failures=(
                    max_consecutive_failures
                ),
            )

        except Exception:
            self.registry.deregister(
                instance_id
            )
            raise

        return descriptor

    def bind_local_handler(
        self,
        instance_id,
        handler,
        max_consecutive_failures=3,
    ):
        if self.load_balancer is None:
            raise RuntimeError(
                "no load balancer is attached"
            )

        if not callable(
            handler
        ):
            raise TypeError(
                "handler must be callable"
            )

        descriptor = self.registry.get(
            instance_id
        )

        instance = ServiceInstance(
            instance_id=(
                descriptor.instance_id
            ),
            service_name=(
                descriptor.service_name
            ),
            handler=handler,
            metadata={
                "discovery_endpoint": (
                    descriptor.endpoint
                ),
                "discovery_metadata": (
                    descriptor._copy(
                        descriptor.metadata
                    )
                ),
            },
            max_consecutive_failures=(
                max_consecutive_failures
            ),
        )

        self.load_balancer.register(
            instance
        )

        self._local_handlers[
            instance_id
        ] = handler

        descriptor.local_bound = True

        return descriptor

    def deregister(
        self,
        instance_id,
    ):
        descriptor = self.registry.get(
            instance_id
        )

        if descriptor.local_bound:
            if self.load_balancer is not None:
                try:
                    self.load_balancer.deregister(
                        instance_id
                    )
                except KeyError:
                    pass

            if instance_id in self._local_handlers:
                del self._local_handlers[
                    instance_id
                ]

        return self.registry.deregister(
            instance_id
        )

    def heartbeat(
        self,
        instance_id,
        now,
    ):
        descriptor = (
            self.registry
            .get(
                instance_id
            )
            .heartbeat(
                now
            )
        )

        self._sync_local_health(
            descriptor
        )

        return descriptor

    def mark_healthy(
        self,
        instance_id,
    ):
        descriptor = (
            self.registry
            .get(
                instance_id
            )
            .mark_healthy()
        )

        self._sync_local_health(
            descriptor
        )

        return descriptor

    def mark_unhealthy(
        self,
        instance_id,
    ):
        descriptor = (
            self.registry
            .get(
                instance_id
            )
            .mark_unhealthy()
        )

        self._sync_local_health(
            descriptor
        )

        return descriptor

    def enable(
        self,
        instance_id,
    ):
        descriptor = (
            self.registry
            .get(
                instance_id
            )
            .enable()
        )

        self._sync_local_health(
            descriptor
        )

        return descriptor

    def disable(
        self,
        instance_id,
    ):
        descriptor = (
            self.registry
            .get(
                instance_id
            )
            .disable()
        )

        self._sync_local_health(
            descriptor
        )

        return descriptor

    def sweep_stale(
        self,
        now,
    ):
        stale_ids = []

        for service_name in self.registry.services():
            for descriptor in self.registry.instances(
                service_name
            ):
                if descriptor.stale(
                    now
                ):
                    descriptor.mark_unhealthy()
                    self._sync_local_health(
                        descriptor
                    )
                    stale_ids.append(
                        descriptor.instance_id
                    )

        return {
            "stale_instance_ids": (
                stale_ids
            ),
            "stale_count": len(
                stale_ids
            ),
        }

    def resolve(
        self,
        service_name,
        now,
        available_only=True,
    ):
        self.sweep_stale(
            now
        )

        result = []

        for descriptor in self.registry.instances(
            service_name
        ):
            if (
                not available_only
                or descriptor.available(
                    now
                )
            ):
                result.append(
                    descriptor.public_dict(
                        now=now
                    )
                )

        return {
            "service_name": (
                service_name
            ),
            "instances": result,
            "count": len(
                result
            ),
            "available_only": bool(
                available_only
            ),
        }

    def list_services(
        self,
        now,
    ):
        self.sweep_stale(
            now
        )

        services = []

        for service_name in self.registry.services():
            total = 0
            available = 0
            local_bound = 0

            for descriptor in self.registry.instances(
                service_name
            ):
                total += 1

                if descriptor.available(
                    now
                ):
                    available += 1

                if descriptor.local_bound:
                    local_bound += 1

            services.append({
                "service_name": (
                    service_name
                ),
                "instances": total,
                "available_instances": (
                    available
                ),
                "local_bound_instances": (
                    local_bound
                ),
            })

        return services

    def status(
        self,
        now,
    ):
        services = self.list_services(
            now
        )

        total = 0
        available = 0
        local_bound = 0

        for service in services:
            total += service[
                "instances"
            ]
            available += service[
                "available_instances"
            ]
            local_bound += service[
                "local_bound_instances"
            ]

        return {
            "ready": True,
            "service_count": len(
                services
            ),
            "instance_count": total,
            "available_instance_count": (
                available
            ),
            "local_bound_instance_count": (
                local_bound
            ),
            "load_balancer_attached": (
                self.load_balancer
                is not None
            ),
            "services": services,
        }

    def _sync_local_health(
        self,
        descriptor,
    ):
        if (
            not descriptor.local_bound
            or self.load_balancer is None
        ):
            return

        try:
            instance = (
                self.load_balancer
                .registry
                .get(
                    descriptor.instance_id
                )
            )
        except KeyError:
            descriptor.local_bound = False
            return

        if (
            descriptor.healthy
            and descriptor.enabled
        ):
            instance.mark_healthy()
            instance.resume()
        else:
            instance.mark_unhealthy()

            if not descriptor.enabled:
                instance.pause()
