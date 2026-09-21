class MetricDefinition:
    TYPES = (
        "counter",
        "gauge",
        "histogram",
    )

    def __init__(
        self,
        name,
        metric_type,
        description="",
        unit=None,
        label_names=None,
        buckets=None,
    ):
        if not isinstance(
            name,
            str,
        ) or name == "":
            raise ValueError(
                "metric name must be non-empty str"
            )

        if metric_type not in self.TYPES:
            raise ValueError(
                "unsupported metric type"
            )

        if not isinstance(
            description,
            str,
        ):
            raise TypeError(
                "description must be str"
            )

        if unit is not None and not isinstance(
            unit,
            str,
        ):
            raise TypeError(
                "unit must be str or None"
            )

        if label_names is None:
            label_names = []

        LabelSet(
            label_names,
            {
                name: ""
                for name in label_names
            },
        )

        normalized_buckets = None

        if metric_type == "histogram":
            if buckets is None:
                buckets = [
                    0.01,
                    0.05,
                    0.1,
                    0.25,
                    0.5,
                    1.0,
                    2.5,
                    5.0,
                    10.0,
                ]

            if not isinstance(
                buckets,
                (list, tuple),
            ) or len(
                buckets
            ) == 0:
                raise ValueError(
                    "histogram buckets must be non-empty list/tuple"
                )

            normalized_buckets = []

            previous = None

            for boundary in buckets:
                if (
                    not isinstance(
                        boundary,
                        (int, float),
                    )
                    or isinstance(
                        boundary,
                        bool,
                    )
                ):
                    raise TypeError(
                        "histogram bucket boundaries must be numeric"
                    )

                boundary = float(
                    boundary
                )

                if previous is not None and boundary <= previous:
                    raise ValueError(
                        "histogram buckets must be strictly increasing"
                    )

                normalized_buckets.append(
                    boundary
                )
                previous = boundary

        elif buckets is not None:
            raise ValueError(
                "buckets only apply to histogram metrics"
            )

        self.name = name
        self.metric_type = (
            metric_type
        )
        self.description = (
            description
        )
        self.unit = unit
        self.label_names = list(
            label_names
        )
        self.buckets = (
            normalized_buckets
        )

    def public_dict(
        self,
    ):
        return {
            "name": self.name,
            "metric_type": (
                self.metric_type
            ),
            "description": (
                self.description
            ),
            "unit": self.unit,
            "label_names": list(
                self.label_names
            ),
            "buckets": (
                None
                if self.buckets
                is None
                else list(
                    self.buckets
                )
            ),
        }

    @classmethod
    def from_dict(
        cls,
        value,
    ):
        if not isinstance(
            value,
            dict,
        ):
            raise TypeError(
                "metric definition state must be dict"
            )

        return cls(
            name=value[
                "name"
            ],
            metric_type=value[
                "metric_type"
            ],
            description=value.get(
                "description",
                "",
            ),
            unit=value.get(
                "unit"
            ),
            label_names=value.get(
                "label_names",
                [],
            ),
            buckets=value.get(
                "buckets"
            ),
        )


class MetricSeries:
    def __init__(
        self,
        definition,
        labels,
    ):
        if not isinstance(
            definition,
            MetricDefinition,
        ):
            raise TypeError(
                "definition must be MetricDefinition"
            )

        if not isinstance(
            labels,
            LabelSet,
        ):
            raise TypeError(
                "labels must be LabelSet"
            )

        self.definition = definition
        self.labels = labels
        self.last_updated = None
        self.samples = 0

        if definition.metric_type == "counter":
            self.value = 0.0

        elif definition.metric_type == "gauge":
            self.value = 0.0

        else:
            self.count = 0
            self.sum = 0.0
            self.minimum = None
            self.maximum = None
            self.bucket_counts = [
                0
                for _ in definition.buckets
            ]

    def increment(
        self,
        amount,
        timestamp,
    ):
        if self.definition.metric_type not in (
            "counter",
            "gauge",
        ):
            raise TypeError(
                "increment only applies to counter/gauge metrics"
            )

        numeric = self._numeric(
            amount
        )

        if (
            self.definition.metric_type
            == "counter"
            and numeric < 0
        ):
            raise ValueError(
                "counter increment cannot be negative"
            )

        self.value += numeric
        self._touch(
            timestamp
        )

        return self

    def set_value(
        self,
        value,
        timestamp,
    ):
        if self.definition.metric_type != "gauge":
            raise TypeError(
                "set_value only applies to gauge metrics"
            )

        self.value = self._numeric(
            value
        )

        self._touch(
            timestamp
        )

        return self

    def observe(
        self,
        value,
        timestamp,
    ):
        if self.definition.metric_type != "histogram":
            raise TypeError(
                "observe only applies to histogram metrics"
            )

        numeric = self._numeric(
            value
        )

        self.count += 1
        self.sum += numeric

        if (
            self.minimum is None
            or numeric < self.minimum
        ):
            self.minimum = numeric

        if (
            self.maximum is None
            or numeric > self.maximum
        ):
            self.maximum = numeric

        index = 0

        while index < len(
            self.definition.buckets
        ):
            if numeric <= self.definition.buckets[
                index
            ]:
                self.bucket_counts[
                    index
                ] += 1

            index += 1

        self._touch(
            timestamp
        )

        return self

    def snapshot(
        self,
    ):
        base = {
            "labels": (
                self.labels
                .to_dict()
            ),
            "last_updated": (
                self.last_updated
            ),
            "samples": (
                self.samples
            ),
        }

        if self.definition.metric_type in (
            "counter",
            "gauge",
        ):
            base[
                "value"
            ] = self.value

            return base

        buckets = []
        index = 0

        while index < len(
            self.definition.buckets
        ):
            buckets.append({
                "le": (
                    self.definition
                    .buckets[
                        index
                    ]
                ),
                "count": (
                    self.bucket_counts[
                        index
                    ]
                ),
            })

            index += 1

        base[
            "count"
        ] = self.count
        base[
            "sum"
        ] = self.sum
        base[
            "minimum"
        ] = self.minimum
        base[
            "maximum"
        ] = self.maximum
        base[
            "buckets"
        ] = buckets

        return base

    def export_state(
        self,
    ):
        state = {
            "labels": (
                self.labels
                .to_dict()
            ),
            "last_updated": (
                self.last_updated
            ),
            "samples": (
                self.samples
            ),
        }

        if self.definition.metric_type in (
            "counter",
            "gauge",
        ):
            state[
                "value"
            ] = self.value
        else:
            state[
                "count"
            ] = self.count
            state[
                "sum"
            ] = self.sum
            state[
                "minimum"
            ] = self.minimum
            state[
                "maximum"
            ] = self.maximum
            state[
                "bucket_counts"
            ] = list(
                self.bucket_counts
            )

        return state

    def load_state(
        self,
        state,
    ):
        self.last_updated = state.get(
            "last_updated"
        )
        self.samples = int(
            state.get(
                "samples",
                0,
            )
        )

        if self.definition.metric_type in (
            "counter",
            "gauge",
        ):
            self.value = float(
                state.get(
                    "value",
                    0.0,
                )
            )
        else:
            self.count = int(
                state.get(
                    "count",
                    0,
                )
            )
            self.sum = float(
                state.get(
                    "sum",
                    0.0,
                )
            )
            self.minimum = state.get(
                "minimum"
            )
            self.maximum = state.get(
                "maximum"
            )
            self.bucket_counts = [
                int(
                    item
                )
                for item in state.get(
                    "bucket_counts",
                    []
                )
            ]

            if len(
                self.bucket_counts
            ) != len(
                self.definition.buckets
            ):
                raise ValueError(
                    "histogram bucket state size mismatch"
                )

        return self

    def _touch(
        self,
        timestamp,
    ):
        if (
            not isinstance(
                timestamp,
                int,
            )
            or timestamp < 0
        ):
            raise ValueError(
                "timestamp must be non-negative int"
            )

        if (
            self.last_updated
            is not None
            and timestamp
            < self.last_updated
        ):
            raise ValueError(
                "metric timestamp cannot move backwards"
            )

        self.last_updated = timestamp
        self.samples += 1

    def _numeric(
        self,
        value,
    ):
        if (
            not isinstance(
                value,
                (int, float),
            )
            or isinstance(
                value,
                bool,
            )
        ):
            raise TypeError(
                "metric value must be numeric"
            )

        return float(
            value
        )
