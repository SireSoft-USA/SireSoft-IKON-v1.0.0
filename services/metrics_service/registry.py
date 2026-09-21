class MetricsRegistry:
    """
    Metric-definition registry and per-label time-series store.
    """

    def __init__(
        self,
    ):
        self._definitions = {}
        self._definition_order = []
        self._series = {}

    def define(
        self,
        name,
        metric_type,
        description="",
        unit=None,
        label_names=None,
        buckets=None,
    ):
        if name in self._definitions:
            raise ValueError(
                "metric already defined: "
                + str(
                    name
                )
            )

        definition = (
            MetricDefinition(
                name=name,
                metric_type=metric_type,
                description=description,
                unit=unit,
                label_names=label_names,
                buckets=buckets,
            )
        )

        self._definitions[
            name
        ] = definition

        self._definition_order.append(
            name
        )

        self._series[
            name
        ] = {}

        return definition

    def get_definition(
        self,
        name,
    ):
        if name not in self._definitions:
            raise KeyError(
                "metric not defined: "
                + str(
                    name
                )
            )

        return self._definitions[
            name
        ]

    def list_definitions(
        self,
    ):
        return [
            self._definitions[
                name
            ].public_dict()
            for name
            in self._definition_order
        ]

    def increment(
        self,
        name,
        amount,
        timestamp,
        labels=None,
    ):
        series = self._series_for(
            name,
            labels,
        )

        series.increment(
            amount,
            timestamp,
        )

        return self._snapshot_one(
            name,
            series,
        )

    def set_gauge(
        self,
        name,
        value,
        timestamp,
        labels=None,
    ):
        series = self._series_for(
            name,
            labels,
        )

        series.set_value(
            value,
            timestamp,
        )

        return self._snapshot_one(
            name,
            series,
        )

    def observe(
        self,
        name,
        value,
        timestamp,
        labels=None,
    ):
        series = self._series_for(
            name,
            labels,
        )

        series.observe(
            value,
            timestamp,
        )

        return self._snapshot_one(
            name,
            series,
        )

    def metric_snapshot(
        self,
        name,
    ):
        definition = self.get_definition(
            name
        )

        series_rows = []

        for key in self._sorted_series_keys(
            name
        ):
            series_rows.append(
                self._series[
                    name
                ][
                    key
                ].snapshot()
            )

        return {
            "definition": (
                definition
                .public_dict()
            ),
            "series": series_rows,
            "series_count": len(
                series_rows
            ),
        }

    def snapshot(
        self,
    ):
        return {
            "metrics": [
                self.metric_snapshot(
                    name
                )
                for name
                in self._definition_order
            ],
            "metric_count": len(
                self._definition_order
            ),
            "series_count": sum(
                len(
                    self._series[
                        name
                    ]
                )
                for name
                in self._definition_order
            ),
        }

    def export_state(
        self,
    ):
        metrics = []

        for name in self._definition_order:
            definition = self._definitions[
                name
            ]

            metrics.append({
                "definition": (
                    definition
                    .public_dict()
                ),
                "series": [
                    self._series[
                        name
                    ][
                        key
                    ].export_state()
                    for key in self._sorted_series_keys(
                        name
                    )
                ],
            })

        return {
            "metrics": metrics,
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
                "metrics registry state must be dict"
            )

        definitions = {}
        definition_order = []
        series = {}

        for metric_state in state.get(
            "metrics",
            [],
        ):
            definition = (
                MetricDefinition
                .from_dict(
                    metric_state[
                        "definition"
                    ]
                )
            )

            if definition.name in definitions:
                raise ValueError(
                    "duplicate metric definition in state"
                )

            definitions[
                definition.name
            ] = definition

            definition_order.append(
                definition.name
            )

            series[
                definition.name
            ] = {}

            for series_state in metric_state.get(
                "series",
                [],
            ):
                labels = LabelSet(
                    definition.label_names,
                    series_state.get(
                        "labels",
                        {},
                    ),
                )

                key = labels.key()

                if key in series[
                    definition.name
                ]:
                    raise ValueError(
                        "duplicate metric series in state"
                    )

                item = MetricSeries(
                    definition,
                    labels,
                )

                item.load_state(
                    series_state
                )

                series[
                    definition.name
                ][
                    key
                ] = item

        self._definitions = definitions
        self._definition_order = (
            definition_order
        )
        self._series = series

        return self

    def _series_for(
        self,
        name,
        labels,
    ):
        definition = self.get_definition(
            name
        )

        label_set = LabelSet(
            definition.label_names,
            labels,
        )

        key = label_set.key()

        if key not in self._series[
            name
        ]:
            self._series[
                name
            ][
                key
            ] = MetricSeries(
                definition,
                label_set,
            )

        return self._series[
            name
        ][
            key
        ]

    def _snapshot_one(
        self,
        name,
        series,
    ):
        return {
            "metric": name,
            "metric_type": (
                self._definitions[
                    name
                ].metric_type
            ),
            "series": (
                series.snapshot()
            ),
        }

    def _sorted_series_keys(
        self,
        name,
    ):
        keys = list(
            self._series[
                name
            ].keys()
        )

        keys.sort()

        return keys
