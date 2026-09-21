class ObservabilitySnapshot:
    """
    Read-oriented diagnostic aggregate.
    """

    def __init__(
        self,
        observability,
    ):
        if not isinstance(
            observability,
            RuntimeObservability,
        ):
            raise TypeError(
                "observability must be RuntimeObservability"
            )

        self.observability = observability

    def capture(
        self,
        log_limit=20,
        trace_limit=20,
        include_health=True,
    ):
        if not isinstance(
            log_limit,
            int,
        ) or log_limit <= 0:
            raise ValueError(
                "log_limit must be positive int"
            )

        if not isinstance(
            trace_limit,
            int,
        ) or trace_limit <= 0:
            raise ValueError(
                "trace_limit must be positive int"
            )

        health = None

        if (
            include_health
            and self.observability
            .health_manager
            is not None
        ):
            health = (
                self.observability
                .health_manager
                .check()
            )

        return {
            "status": (
                self.observability
                .status()
            ),
            "recent_logs": (
                self.observability
                .logging_manager
                .query(
                    limit=log_limit,
                    newest_first=True,
                )
            ),
            "metrics": (
                self.observability
                .metrics_manager
                .snapshot()
            ),
            "recent_traces": (
                self.observability
                .tracing_manager
                .list_traces(
                    limit=trace_limit,
                    newest_first=True,
                )
            ),
            "health": health,
        }
