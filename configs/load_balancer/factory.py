class LoadBalancerConfigFactory:
    """
    Builds the real protocol-aware LoadBalancer from declarative topology and
    runtime-only service handlers.
    """

    def build_strategy(self, config):
        if not isinstance(
            config,
            LoadBalancerConfig,
        ):
            raise TypeError(
                "config must be LoadBalancerConfig"
            )

        if config.strategy == "round_robin":
            return RoundRobinStrategy()

        if config.strategy == "least_load":
            return LeastLoadStrategy()

        if config.strategy == "adaptive":
            return AdaptiveStrategy()

        raise ValueError(
            "unsupported load-balancer strategy"
        )

    def build(
        self,
        config,
        handlers=None,
    ):
        if not isinstance(
            config,
            LoadBalancerConfig,
        ):
            raise TypeError(
                "config must be LoadBalancerConfig"
            )

        LoadBalancerConfigValidator().require_valid(
            config
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

        balancer = LoadBalancer(
            strategy=self.build_strategy(
                config
            ),
            max_attempts=(
                config.max_attempts
            ),
        )

        for item in (
            config.enabled_instances()
        ):
            handler = self._resolve_handler(
                handlers,
                item,
            )

            instance = ServiceInstance(
                instance_id=(
                    item.instance_id
                ),
                service_name=(
                    item.service_name
                ),
                handler=handler,
                metadata=(
                    item.metadata
                ),
                max_consecutive_failures=(
                    item
                    .max_consecutive_failures
                ),
            )

            if not item.healthy:
                instance.mark_unhealthy()

            if not item.accepting_requests:
                instance.pause()

            balancer.register(
                instance
            )

        return balancer

    def _resolve_handler(
        self,
        handlers,
        item,
    ):
        if item.handler_key in handlers:
            candidate = handlers[
                item.handler_key
            ]

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
                "missing load-balancer handler for "
                + item.instance_id
                + " using key "
                + item.handler_key
            )

        if hasattr(
            candidate,
            "handle",
        ):
            candidate = (
                candidate.handle
            )

        if not callable(candidate):
            raise TypeError(
                "resolved load-balancer handler must be callable or expose handle()"
            )

        return candidate
