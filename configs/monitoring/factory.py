class MonitoringConfigFactory:
    """
    Resolves runtime service handlers into deterministic ServiceProbe objects.
    """

    def build_manager(
        self,
        config,
        handlers,
        load_balancer=None,
    ):
        if not isinstance(
            config,
            MonitoringConfig,
        ):
            raise TypeError(
                "config must be MonitoringConfig"
            )

        MonitoringConfigValidator().require_valid(
            config
        )

        if not isinstance(
            handlers,
            dict,
        ):
            raise TypeError(
                "handlers must be dict"
            )

        if (
            config.attach_load_balancer
            and load_balancer is None
        ):
            raise ValueError(
                "monitoring config requires load_balancer"
            )

        manager = MonitoringManager(
            load_balancer=(
                load_balancer
                if config
                .attach_load_balancer
                else None
            )
        )

        for probe in (
            config.enabled_probes()
        ):
            handler = self._resolve_handler(
                handlers,
                probe,
            )

            manager.register_probe(
                ServiceProbe(
                    probe_id=(
                        probe.probe_id
                    ),
                    service_name=(
                        probe.service_name
                    ),
                    handler=handler,
                    operation=(
                        probe.operation
                    ),
                    payload=probe.payload,
                    required=(
                        probe.required
                    ),
                    readiness_path=(
                        probe.readiness_path
                    ),
                    metadata=(
                        probe.metadata
                    ),
                )
            )

        return manager

    def build_service(
        self,
        config,
        handlers,
        load_balancer=None,
    ):
        return MonitoringService(
            self.build_manager(
                config,
                handlers,
                load_balancer=(
                    load_balancer
                ),
            )
        )

    def _resolve_handler(
        self,
        handlers,
        probe,
    ):
        if probe.probe_id in handlers:
            candidate = handlers[
                probe.probe_id
            ]

        elif (
            probe.service_name
            in handlers
        ):
            candidate = handlers[
                probe.service_name
            ]

        else:
            raise KeyError(
                "missing monitoring handler for probe "
                + probe.probe_id
                + " / service "
                + probe.service_name
            )

        if hasattr(
            candidate,
            "handle",
        ):
            candidate = (
                candidate.handle
            )

        if not callable(
            candidate
        ):
            raise TypeError(
                "resolved monitoring handler must be callable or expose handle()"
            )

        return candidate
