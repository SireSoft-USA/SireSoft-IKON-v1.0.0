class ServiceDiscoveryConfigFactory:
    """
    Builds lease-based discovery from serialized topology plus runtime-only
    handler/time dependencies.
    """

    def build_manager(
        self,
        config,
        load_balancer=None,
    ):
        if not isinstance(
            config,
            ServiceDiscoveryConfig,
        ):
            raise TypeError(
                "config must be ServiceDiscoveryConfig"
            )

        ServiceDiscoveryConfigValidator().require_valid(
            config
        )

        if (
            config.attach_load_balancer
            and load_balancer is None
        ):
            raise ValueError(
                "service discovery config requires load_balancer"
            )

        return ServiceDiscoveryManager(
            load_balancer=(
                load_balancer
                if config.attach_load_balancer
                else None
            )
        )

    def initialize(
        self,
        config,
        now,
        handlers=None,
        load_balancer=None,
        manager=None,
    ):
        if not isinstance(
            now,
            int,
        ) or now < 0:
            raise ValueError(
                "now must be non-negative int"
            )

        if handlers is None:
            handlers = {}

        if not isinstance(
            handlers,
            dict,
        ):
            raise TypeError(
                "handlers must be dict or None"
            )

        if manager is None:
            manager = self.build_manager(
                config,
                load_balancer=(
                    load_balancer
                ),
            )

        if not isinstance(
            manager,
            ServiceDiscoveryManager,
        ):
            raise TypeError(
                "manager must be ServiceDiscoveryManager or None"
            )

        registered = []

        for item in config.enabled_instances():
            if item.local():
                handler = self._resolve_handler(
                    handlers,
                    item,
                )

                descriptor = (
                    manager.register_local(
                        instance_id=(
                            item.instance_id
                        ),
                        service_name=(
                            item.service_name
                        ),
                        handler=handler,
                        now=now,
                        endpoint=(
                            item.endpoint
                        ),
                        lease_seconds=(
                            item.lease_seconds
                        ),
                        metadata=(
                            item.metadata
                        ),
                        max_consecutive_failures=(
                            item
                            .max_consecutive_failures
                        ),
                    )
                )
            else:
                descriptor = (
                    manager.register_instance(
                        instance_id=(
                            item.instance_id
                        ),
                        service_name=(
                            item.service_name
                        ),
                        endpoint=(
                            item.endpoint
                        ),
                        now=now,
                        lease_seconds=(
                            item.lease_seconds
                        ),
                        metadata=(
                            item.metadata
                        ),
                    )
                )

            registered.append(
                descriptor
            )

        return {
            "manager": manager,
            "registered": registered,
            "registered_count": len(
                registered
            ),
        }

    def build_service(
        self,
        config,
        now,
        handlers=None,
        load_balancer=None,
    ):
        result = self.initialize(
            config,
            now=now,
            handlers=handlers,
            load_balancer=(
                load_balancer
            ),
        )

        return ServiceDiscoveryService(
            result["manager"]
        )

    def _resolve_handler(
        self,
        handlers,
        item,
    ):
        key = item.local_handler_key

        if key in handlers:
            candidate = handlers[key]
        elif item.instance_id in handlers:
            candidate = handlers[
                item.instance_id
            ]
        elif item.service_name in handlers:
            candidate = handlers[
                item.service_name
            ]
        else:
            raise KeyError(
                "missing local handler for discovery instance "
                + item.instance_id
                + " using key "
                + str(key)
            )

        if hasattr(candidate, "handle"):
            candidate = candidate.handle

        if not callable(candidate):
            raise TypeError(
                "resolved local discovery handler must be callable or expose handle()"
            )

        return candidate
