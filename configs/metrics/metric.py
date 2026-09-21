class MetricConfig:
    """
    Serializable metric-definition configuration.
    """

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
        enabled=True,
        metadata=None,
    ):
        if not isinstance(
            name,
            str,
        ) or name == "":
            raise ValueError(
                "name must be non-empty str"
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

        if not isinstance(
            label_names,
            (list, tuple),
        ):
            raise TypeError(
                "label_names must be list/tuple or None"
            )

        normalized_labels = []
        seen = {}

        for label_name in label_names:
            if not isinstance(
                label_name,
                str,
            ) or label_name == "":
                raise ValueError(
                    "label names must be non-empty strings"
                )

            if label_name in seen:
                raise ValueError(
                    "duplicate label name: "
                    + label_name
                )

            seen[
                label_name
            ] = True
            normalized_labels.append(
                label_name
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

                numeric = float(
                    boundary
                )

                if (
                    previous is not None
                    and numeric <= previous
                ):
                    raise ValueError(
                        "histogram buckets must be strictly increasing"
                    )

                normalized_buckets.append(
                    numeric
                )

                previous = numeric

        elif buckets is not None:
            raise ValueError(
                "buckets only apply to histogram metrics"
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

        self.name = name
        self.metric_type = (
            metric_type
        )
        self.description = (
            description
        )
        self.unit = unit
        self.label_names = (
            normalized_labels
        )
        self.buckets = (
            normalized_buckets
        )
        self.enabled = bool(
            enabled
        )
        self.metadata = self._copy(
            metadata
        )

    def to_dict(
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
            "enabled": (
                self.enabled
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
