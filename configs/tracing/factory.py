class TracingConfigFactory:
    """
    Builds TracingManager while keeping service dependencies injectable.
    """

    def build_sampler(
        self,
        config,
    ):
        if not isinstance(
            config,
            TracingConfig,
        ):
            raise TypeError(
                "config must be TracingConfig"
            )

        return DeterministicTraceSampler(
            numerator=(
                config
                .sampler
                .numerator
            ),
            denominator=(
                config
                .sampler
                .denominator
            ),
        )

    def build_manager(
        self,
        config,
        metrics_manager=None,
        event_bus=None,
        persistence=None,
    ):
        if not isinstance(
            config,
            TracingConfig,
        ):
            raise TypeError(
                "config must be TracingConfig"
            )

        TracingConfigValidator().require_valid(
            config
        )

        if (
            config.attach_metrics
            and metrics_manager
            is None
        ):
            raise ValueError(
                "metrics_manager is required when attach_metrics=True"
            )

        if (
            config.publish_events
            and event_bus
            is None
        ):
            raise ValueError(
                "event_bus is required when publish_events=True"
            )

        return TracingManager(
            sampler=(
                self.build_sampler(
                    config
                )
            ),
            persistence=(
                persistence
            ),
            metrics_manager=(
                metrics_manager
                if config.attach_metrics
                else None
            ),
            event_bus=(
                event_bus
                if config.publish_events
                else None
            ),
        )

    def initialize(
        self,
        config,
        metrics_manager=None,
        event_bus=None,
        persistence=None,
        load_persisted=False,
    ):
        manager = self.build_manager(
            config,
            metrics_manager=(
                metrics_manager
            ),
            event_bus=(
                event_bus
            ),
            persistence=(
                persistence
            ),
        )

        if (
            load_persisted
            and config.persistence_path
            is not None
        ):
            manager.load_state_file(
                config.persistence_path
            )

        return manager
