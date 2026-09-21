class SchedulerConfigFactory:
    def build_manager(
        self,
        config,
        job_queue,
        event_bus=None,
        persistence=None,
    ):
        if not isinstance(
            config,
            SchedulerConfig,
        ):
            raise TypeError(
                "config must be SchedulerConfig"
            )

        SchedulerConfigValidator().require_valid(
            config,
            job_queue=job_queue,
        )

        if (
            config.attach_event_bus
            and event_bus is None
        ):
            raise ValueError(
                "scheduler config requires event_bus"
            )

        manager = SchedulerManager(
            job_queue=job_queue,
            persistence=persistence,
            event_bus=(
                event_bus
                if config.attach_event_bus
                else None
            ),
        )

        if config.load_state_on_start:
            manager.load_state_file(
                config.state_path
            )
            return manager

        for item in config.tasks:
            manager.create_task(
                task_id=item.task_id,
                queue_name=item.queue_name,
                payload=item.payload,
                next_run_at=item.next_run_at,
                recurrence=item.recurrence.to_rule(),
                priority=item.priority,
                max_attempts=item.max_attempts,
                metadata=item.metadata,
                enabled=item.enabled,
            )

        return manager

    def build_service(
        self,
        config,
        job_queue,
        event_bus=None,
        persistence=None,
    ):
        return SchedulerService(
            self.build_manager(
                config,
                job_queue,
                event_bus=event_bus,
                persistence=persistence,
            )
        )
