class MetricsConfigFactory:
    """
    Builds MetricsManager definitions from serializable configuration.
    """

    def build_manager(
        self,
        config,
        persistence=None,
    ):
        if not isinstance(
            config,
            MetricsConfig,
        ):
            raise TypeError(
                "config must be MetricsConfig"
            )

        MetricsConfigValidator().require_valid(
            config
        )

        manager = MetricsManager(
            persistence=(
                persistence
            )
        )

        for metric in config.enabled_metrics():
            manager.define(
                name=metric.name,
                metric_type=(
                    metric.metric_type
                ),
                description=(
                    metric.description
                ),
                unit=metric.unit,
                label_names=(
                    metric.label_names
                ),
                buckets=metric.buckets,
            )

        return manager

    def initialize(
        self,
        config,
        manager=None,
        load_persisted=False,
    ):
        if not isinstance(
            config,
            MetricsConfig,
        ):
            raise TypeError(
                "config must be MetricsConfig"
            )

        if manager is None:
            manager = self.build_manager(
                config
            )

        if not isinstance(
            manager,
            MetricsManager,
        ):
            raise TypeError(
                "manager must be MetricsManager or None"
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
