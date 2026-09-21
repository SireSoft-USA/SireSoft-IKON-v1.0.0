class MetricsConfigCodec:
    def __init__(
        self,
        parser=None,
    ):
        self.parser = (
            JSONParser()
            if parser is None
            else parser
        )

    def decode_text(
        self,
        text,
    ):
        if not isinstance(
            text,
            str,
        ):
            raise TypeError(
                "metrics config text must be str"
            )

        return self.from_dict(
            self.parser.parse(
                text
            )
        )

    def from_dict(
        self,
        value,
    ):
        if not isinstance(
            value,
            dict,
        ):
            raise ValueError(
                "metrics config root must be object"
            )

        raw_metrics = value.get(
            "metrics"
        )

        if not isinstance(
            raw_metrics,
            list,
        ) or len(
            raw_metrics
        ) == 0:
            raise ValueError(
                "metrics must be non-empty list"
            )

        metrics = []

        for raw in raw_metrics:
            if not isinstance(
                raw,
                dict,
            ):
                raise ValueError(
                    "metric entry must be object"
                )

            metrics.append(
                MetricConfig(
                    name=raw.get(
                        "name"
                    ),
                    metric_type=raw.get(
                        "metric_type"
                    ),
                    description=raw.get(
                        "description",
                        "",
                    ),
                    unit=raw.get(
                        "unit"
                    ),
                    label_names=raw.get(
                        "label_names",
                        [],
                    ),
                    buckets=raw.get(
                        "buckets"
                    ),
                    enabled=raw.get(
                        "enabled",
                        True,
                    ),
                    metadata=raw.get(
                        "metadata",
                        {},
                    ),
                )
            )

        return MetricsConfig(
            metrics=metrics,
            persistence_path=value.get(
                "persistence_path"
            ),
            metadata=value.get(
                "metadata",
                {},
            ),
        )
