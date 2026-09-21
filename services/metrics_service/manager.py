class MetricsManager:
    """
    High-level metrics orchestration.

    It exposes typed metric operations and snapshots suitable for monitoring,
    runtime diagnostics, and later export adapters.
    """

    def __init__(
        self,
        registry=None,
        persistence=None,
    ):
        self.registry = (
            MetricsRegistry()
            if registry is None
            else registry
        )

        self.persistence = (
            MetricsPersistence()
            if persistence is None
            else persistence
        )

        self.total_updates = 0

    def define(
        self,
        name,
        metric_type,
        description="",
        unit=None,
        label_names=None,
        buckets=None,
    ):
        return self.registry.define(
            name=name,
            metric_type=metric_type,
            description=description,
            unit=unit,
            label_names=label_names,
            buckets=buckets,
        )

    def increment(
        self,
        name,
        timestamp,
        amount=1,
        labels=None,
    ):
        result = (
            self.registry
            .increment(
                name=name,
                amount=amount,
                timestamp=timestamp,
                labels=labels,
            )
        )

        self.total_updates += 1

        return result

    def set_gauge(
        self,
        name,
        value,
        timestamp,
        labels=None,
    ):
        result = (
            self.registry
            .set_gauge(
                name=name,
                value=value,
                timestamp=timestamp,
                labels=labels,
            )
        )

        self.total_updates += 1

        return result

    def observe(
        self,
        name,
        value,
        timestamp,
        labels=None,
    ):
        result = (
            self.registry
            .observe(
                name=name,
                value=value,
                timestamp=timestamp,
                labels=labels,
            )
        )

        self.total_updates += 1

        return result

    def get_metric(
        self,
        name,
    ):
        return self.registry.metric_snapshot(
            name
        )

    def snapshot(
        self,
    ):
        return self.registry.snapshot()

    def save_state(
        self,
        path,
    ):
        return self.persistence.save(
            path,
            self,
        )

    def load_state_file(
        self,
        path,
    ):
        return self.persistence.load(
            path,
            self,
        )

    def export_state(
        self,
    ):
        return {
            "format": (
                "SireLLMMetricsState"
            ),
            "version": 1,
            "total_updates": (
                self.total_updates
            ),
            "registry": (
                self.registry
                .export_state()
            ),
        }

    def load_state(
        self,
        state,
    ):
        if not isinstance(
            state,
            dict,
        ):
            raise TypeError(
                "metrics manager state must be dict"
            )

        if state.get(
            "format"
        ) != "SireLLMMetricsState":
            raise ValueError(
                "invalid metrics state format"
            )

        if int(
            state.get(
                "version",
                0,
            )
        ) != 1:
            raise ValueError(
                "unsupported metrics state version"
            )

        staged = (
            MetricsRegistry()
        )

        staged.load_state(
            state.get(
                "registry",
                {},
            )
        )

        self.registry = staged
        self.total_updates = int(
            state.get(
                "total_updates",
                0,
            )
        )

        return self

    def status(
        self,
    ):
        snapshot = self.snapshot()

        return {
            "ready": True,
            "metric_count": (
                snapshot[
                    "metric_count"
                ]
            ),
            "series_count": (
                snapshot[
                    "series_count"
                ]
            ),
            "total_updates": (
                self.total_updates
            ),
            "metric_types": (
                "counter,gauge,histogram"
            ),
        }


def build_default_metrics_manager():
    manager = MetricsManager()

    manager.define(
        name="requests_total",
        metric_type="counter",
        description=(
            "Total service requests"
        ),
        label_names=[
            "service",
            "operation",
            "outcome",
        ],
    )

    manager.define(
        name="active_requests",
        metric_type="gauge",
        description=(
            "Currently active requests"
        ),
        label_names=[
            "service",
        ],
    )

    manager.define(
        name="request_duration_seconds",
        metric_type="histogram",
        description=(
            "Request duration in seconds"
        ),
        unit="seconds",
        label_names=[
            "service",
            "operation",
        ],
        buckets=[
            0.01,
            0.05,
            0.1,
            0.25,
            0.5,
            1.0,
            2.5,
            5.0,
        ],
    )

    return manager
