class RuntimeCompositionBuilder:
    """
    Composition root for the runtime layer built in Folders 61-75.
    """

    def build(
        self,
        spec,
    ):
        if not isinstance(
            spec,
            RuntimeSystemSpec,
        ):
            raise TypeError(
                "spec must be RuntimeSystemSpec"
            )

        bootstrap_config = (
            RuntimeBootstrapConfig(
                storage_root=(
                    spec.storage_root
                ),
                worker_count=(
                    spec.worker_count
                ),
                queue_capacity=(
                    spec.queue_capacity
                ),
                storage_namespaces=(
                    spec.storage_namespaces
                ),
                process_specs=(
                    spec.process_specs
                ),
                metadata=(
                    spec.metadata
                ),
            )
        )

        application = (
            RuntimeBuilder()
            .build(
                bootstrap_config
            )
        )

        host = ServiceHost()

        for binding in spec.service_bindings:
            host.add(
                binding
            )

        application.lifecycle.register(
            ServiceHostLifecycleAdapter
            .resource(
                name="service_host",
                host=host,
                now_provider=(
                    spec.now
                ),
                dependencies=[
                    "workers",
                ],
                metadata={
                    "composition_root": (
                        True
                    ),
                },
            )
        )

        shutdown_coordinator = (
            ShutdownCoordinator()
        )

        signal_handler = (
            RuntimeSignalHandler(
                shutdown_coordinator
            )
        )

        if spec.enable_signals:
            application.lifecycle.register(
                RuntimeSignalLifecycleAdapter
                .resource(
                    name="signals",
                    signal_handler=(
                        signal_handler
                    ),
                    dependencies=[
                        "service_host",
                    ],
                    metadata={
                        "composition_root": (
                            True
                        ),
                    },
                )
            )

        health = RuntimeHealthManager()

        health.register(
            RuntimeHealthAdapters
            .lifecycle(
                application.lifecycle
            )
        )

        health.register(
            RuntimeHealthAdapters
            .worker_pool(
                application.context
                .get(
                    "worker_pool"
                )
            )
        )

        health.register(
            RuntimeHealthAdapters
            .storage(
                application.storage()
            )
        )

        health.register(
            RuntimeHealthAdapters
            .service_host(
                host,
                spec.now,
            )
        )

        logging_manager = (
            LoggingManager(
                minimum_level="DEBUG",
                max_records=1000,
            )
        )

        metrics_manager = (
            MetricsManager()
        )

        tracing_manager = (
            TracingManager(
                metrics_manager=(
                    metrics_manager
                )
            )
        )

        observability = (
            RuntimeObservability(
                logging_manager=(
                    logging_manager
                ),
                metrics_manager=(
                    metrics_manager
                ),
                tracing_manager=(
                    tracing_manager
                ),
                health_manager=health,
            )
        )

        observability_snapshot = (
            ObservabilitySnapshot(
                observability
            )
        )

        diagnostics = (
            RuntimeDiagnosticCollector(
                runtime_application=(
                    application
                ),
                health_manager=health,
                observability_snapshot=(
                    observability_snapshot
                ),
            )
        )

        recovery_executor = (
            RecoveryExecutor()
        )

        recovery_executor.register(
            "clear_transient_failure_state",
            RecoveryAdapters
            .worker_failure_bookkeeping_handler(
                application.context
                .get(
                    "worker_pool"
                )
            ),
        )

        recovery = RecoveryManager(
            executor=(
                recovery_executor
            )
        )

        maintenance = (
            RuntimeMaintenanceManager(
                host
            )
        )

        control_plane = (
            RuntimeControlPlane(
                runtime_application=(
                    application
                ),
                diagnostic_collector=(
                    diagnostics
                ),
                recovery_manager=(
                    recovery
                ),
                maintenance_manager=(
                    maintenance
                ),
                shutdown_coordinator=(
                    shutdown_coordinator
                ),
            )
        )

        control_service = (
            RuntimeControlService(
                control_plane
            )
        )

        maintenance_dispatcher = (
            MaintenanceDispatcher(
                maintenance_manager=(
                    maintenance
                ),
                dispatcher=(
                    host.dispatch
                ),
            )
        )

        observed_dispatcher = (
            ObservedDispatcher(
                observability=(
                    observability
                ),
                dispatcher=(
                    maintenance_dispatcher
                ),
                time_provider=(
                    spec.now
                ),
            )
        )

        shutdown_bridge = (
            RuntimeShutdownBridge(
                coordinator=(
                    shutdown_coordinator
                ),
                runtime_application=(
                    application
                ),
            )
        )

        components = RuntimeComponents()

        for name, value in (
            (
                "spec",
                spec,
            ),
            (
                "application",
                application,
            ),
            (
                "service_host",
                host,
            ),
            (
                "health",
                health,
            ),
            (
                "logging",
                logging_manager,
            ),
            (
                "metrics",
                metrics_manager,
            ),
            (
                "tracing",
                tracing_manager,
            ),
            (
                "observability",
                observability,
            ),
            (
                "diagnostics",
                diagnostics,
            ),
            (
                "recovery",
                recovery,
            ),
            (
                "maintenance",
                maintenance,
            ),
            (
                "shutdown_coordinator",
                shutdown_coordinator,
            ),
            (
                "signal_handler",
                signal_handler,
            ),
            (
                "control_plane",
                control_plane,
            ),
            (
                "control_service",
                control_service,
            ),
            (
                "request_dispatcher",
                observed_dispatcher,
            ),
            (
                "shutdown_bridge",
                shutdown_bridge,
            ),
        ):
            components.add(
                name,
                value,
            )

        components.seal()

        return RuntimeSystem(
            components
        )
