class TracingConfigValidator:
    def validate(
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

        errors = []
        warnings = []

        numerator = (
            config.sampler.numerator
        )
        denominator = (
            config.sampler.denominator
        )

        if numerator == 0:
            warnings.append({
                "code": (
                    "TRACING_DISABLED_BY_SAMPLER"
                ),
                "message": (
                    "Sampler drops every trace"
                ),
            })

        elif numerator == denominator:
            warnings.append({
                "code": (
                    "FULL_TRACE_SAMPLING"
                ),
                "message": (
                    "Every trace will be sampled"
                ),
            })

        elif (
            denominator >= 10000
        ):
            warnings.append({
                "code": (
                    "HIGH_SAMPLING_DENOMINATOR"
                ),
                "message": (
                    "Sampling denominator is unusually high"
                ),
            })

        if (
            config.publish_events
            and not config.attach_metrics
        ):
            warnings.append({
                "code": (
                    "EVENTS_WITHOUT_METRICS"
                ),
                "message": (
                    "Tracing events are enabled while tracing metrics are disabled"
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
            "sample_ratio": (
                float(
                    numerator
                )
                / float(
                    denominator
                )
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
