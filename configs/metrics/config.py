class MetricsConfig:
    """
    Complete metrics-service configuration.
    """

    def __init__(
        self,
        metrics,
        persistence_path=None,
        metadata=None,
    ):
        if not isinstance(
            metrics,
            (list, tuple),
        ) or len(
            metrics
        ) == 0:
            raise ValueError(
                "metrics must be non-empty list/tuple"
            )

        normalized = []
        seen = {}

        for metric in metrics:
            if not isinstance(
                metric,
                MetricConfig,
            ):
                raise TypeError(
                    "metrics entries must be MetricConfig"
                )

            if metric.name in seen:
                raise ValueError(
                    "duplicate metric name: "
                    + metric.name
                )

            seen[
                metric.name
            ] = True
            normalized.append(
                metric
            )

        if persistence_path is not None and (
            not isinstance(
                persistence_path,
                str,
            )
            or persistence_path == ""
        ):
            raise ValueError(
                "persistence_path must be non-empty str or None"
            )

        if metadata is None:
            metadata = {}

        if not isinstance(
            metadata,
            dict,
        ):
            raise TypeError(
                "metadata must be dict or None"
            )

        self.metrics = normalized
        self.persistence_path = (
            persistence_path
        )
        self.metadata = self._copy(
            metadata
        )

    def metric_map(
        self,
    ):
        return {
            metric.name: metric
            for metric
            in self.metrics
        }

    def enabled_metrics(
        self,
    ):
        return [
            metric
            for metric
            in self.metrics
            if metric.enabled
        ]

    def to_dict(
        self,
    ):
        return {
            "metrics": [
                metric.to_dict()
                for metric
                in self.metrics
            ],
            "persistence_path": (
                self.persistence_path
            ),
            "metadata": self._copy(
                self.metadata
            ),
        }

    def _copy(
        self,
        value,
    ):
        if isinstance(
            value,
            dict,
        ):
            return {
                key: self._copy(
                    value[
                        key
                    ]
                )
                for key
                in value
            }

        if isinstance(
            value,
            (list, tuple),
        ):
            return [
                self._copy(
                    item
                )
                for item
                in value
            ]

        return value
