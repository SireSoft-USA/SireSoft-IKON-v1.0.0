class RuntimeBuilder:
    def build(self, config):
        if not isinstance(config, RuntimeBootstrapConfig):
            raise TypeError(
                "config must be RuntimeBootstrapConfig"
            )

        context = RuntimeContext()

        storage = RuntimeStorage(
            config.storage_root
        )

        worker_pool = WorkerPool(
            worker_count=config.worker_count,
            queue_capacity=config.queue_capacity,
        )

        supervisor = ProcessSupervisor()

        for spec in config.process_specs:
            supervisor.register(spec)

        lifecycle = LifecycleManager()

        lifecycle.register(
            StorageLifecycleAdapter.resource(
                name="storage",
                storage=storage,
                namespaces=config.storage_namespaces,
                metadata={
                    "bootstrap": True,
                },
            )
        )

        lifecycle.register(
            WorkerPoolLifecycleAdapter.resource(
                name="workers",
                worker_pool=worker_pool,
                dependencies=[
                    "storage",
                ],
                metadata={
                    "bootstrap": True,
                },
            )
        )

        if len(config.process_specs) > 0:
            lifecycle.register(
                ProcessSupervisorLifecycleAdapter.resource(
                    name="processes",
                    supervisor=supervisor,
                    process_names=[
                        spec.name
                        for spec in config.process_specs
                    ],
                    dependencies=[
                        "workers",
                    ],
                    metadata={
                        "bootstrap": True,
                    },
                    timeout=config.process_shutdown_timeout,
                )
            )

        context.register(
            "config",
            config,
        )
        context.register(
            "storage",
            storage,
        )
        context.register(
            "worker_pool",
            worker_pool,
        )
        context.register(
            "process_supervisor",
            supervisor,
        )
        context.register(
            "lifecycle",
            lifecycle,
        )
        context.seal()

        return RuntimeApplication(
            context=context,
            lifecycle=lifecycle,
        )
