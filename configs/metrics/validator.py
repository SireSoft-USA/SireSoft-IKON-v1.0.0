class MetricsConfigValidator:
    """
    Operational checks for metrics definitions before manager construction.
    """

    def validate(
        self,
        config,
    ):
        if not isinstance(
            config,
            MetricsConfig,
        ):
            raise TypeError(
                "config must be MetricsConfig"
            )

        errors = []
        warnings = []

        enabled = (
            config.enabled_metrics()
        )

        if len(
            enabled
        ) == 0:
            errors.append({
                "code": (
                    "NO_ENABLED_METRICS"
                ),
                "message": (
                    "At least one metric must be enabled"
                ),
            })

        for metric in config.metrics:
            if (
                metric.metric_type
                == "histogram"
                and len(
                    metric.buckets
                )
                > 100
            ):
                warnings.append({
                    "code": (
                        "VERY_LARGE_HISTOGRAM"
                    ),
                    "metric": (
                        metric.name
                    ),
                    "message": (
                        "Histogram has unusually many buckets"
                    ),
                })

            if (
                len(
                    metric.label_names
                )
                > 8
            ):
                warnings.append({
                    "code": (
                        "HIGH_LABEL_CARDINALITY_RISK"
                    ),
                    "metric": (
                        metric.name
                    ),
                    "message": (
                        "Metric has many label dimensions"
                    ),
                })

            if (
                metric.metric_type
                == "counter"
                and metric.unit
                == "seconds"
            ):
                warnings.append({
                    "code": (
                        "COUNTER_SECONDS_UNIT"
                    ),
                    "metric": (
                        metric.name
                    ),
                    "message": (
                        "Counter uses seconds unit; histogram/gauge may be more appropriate"
                    ),
                })

        return {
            "valid": (
                len(
                    errors
                )
                == 0
            ),
            "error_count": len(
                errors
            ),
            "warning_count": len(
                warnings
            ),
            "errors": errors,
            "warnings": warnings,
            "enabled_metric_count": len(
                enabled
            ),
        }

    def require_valid(
        self,
        config,
    ):
        result = self.validate(
            config
        )

        if not result[
            "valid"
        ]:
            first = result[
                "errors"
            ][
                0
            ]

            raise ValueError(
                first[
                    "code"
                ]
                + ": "
                + first[
                    "message"
                ]
            )

        return result
