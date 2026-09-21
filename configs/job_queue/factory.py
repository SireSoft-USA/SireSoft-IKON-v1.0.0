class JobQueueConfigFactory:
    """
    Builds queue topology and synchronous workers from typed configuration.
    """

    def build_manager(
        self,
        config,
        event_bus=None,
        persistence=None,
    ):
        if not isinstance(
            config,
            JobQueueConfig,
        ):
            raise TypeError(
                "config must be JobQueueConfig"
            )

        JobQueueConfigValidator().require_valid(
            config
        )

        if (
            config.attach_event_bus
            and event_bus is None
        ):
            raise ValueError(
                "job queue config requires event_bus"
            )

        manager = JobQueueManager(
            persistence=persistence,
            event_bus=(
                event_bus
                if config
                .attach_event_bus
                else None
            ),
        )

        if config.load_state_on_start:
            manager.load_state_file(
                config.state_path
            )

            return manager

        for queue in (
            config.enabled_queues()
        ):
            manager.create_queue(
                queue_name=(
                    queue.queue_name
                ),
                default_lease_seconds=(
                    queue
                    .default_lease_seconds
                ),
                default_max_attempts=(
                    queue
                    .default_max_attempts
                ),
            )

        return manager

    def build_workers(
        self,
        config,
        manager,
        handlers=None,
    ):
        if not isinstance(
            manager,
            JobQueueManager,
        ):
            raise TypeError(
                "manager must be JobQueueManager"
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

        workers = []

        for item in (
            config.enabled_workers()
        ):
            handler = self._resolve_handler(
                handlers,
                item,
            )

            workers.append(
                JobWorker(
                    worker_id=(
                        item.worker_id
                    ),
                    queue_name=(
                        item.queue_name
                    ),
                    manager=manager,
                    handler=handler,
                    lease_seconds=(
                        item.lease_seconds
                    ),
                    retry_delay_seconds=(
                        item
                        .retry_delay_seconds
                    ),
                )
            )

        return workers

    def initialize(
        self,
        config,
        event_bus=None,
        persistence=None,
        handlers=None,
    ):
        manager = self.build_manager(
            config,
            event_bus=event_bus,
            persistence=persistence,
        )

        workers = self.build_workers(
            config,
            manager,
            handlers=handlers,
        )

        return {
            "manager": manager,
            "workers": workers,
            "queue_count": (
                manager.status()[
                    "queue_count"
                ]
            ),
            "worker_count": len(
                workers
            ),
        }

    def build_service(
        self,
        config,
        event_bus=None,
        persistence=None,
        handlers=None,
    ):
        result = self.initialize(
            config,
            event_bus=event_bus,
            persistence=persistence,
            handlers=handlers,
        )

        return JobQueueService(
            result[
                "manager"
            ]
        )

    def _resolve_handler(
        self,
        handlers,
        item,
    ):
        if (
            item.handler_key
            not in handlers
        ):
            raise KeyError(
                "missing job worker handler: "
                + item.handler_key
            )

        candidate = handlers[
            item.handler_key
        ]

        if hasattr(
            candidate,
            "handle_job",
        ):
            candidate = (
                candidate.handle_job
            )

        if not callable(
            candidate
        ):
            raise TypeError(
                "job worker handler must be callable or expose handle_job()"
            )

        return candidate
