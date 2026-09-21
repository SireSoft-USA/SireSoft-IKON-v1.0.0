class LoggingConfigValidator:
    def validate(
        self,
        config,
    ):
        if not isinstance(
            config,
            LoggingConfig,
        ):
            raise TypeError(
                "config must be LoggingConfig"
            )

        errors = []
        warnings = []

        enabled = (
            config.enabled_sinks()
        )

        if len(
            enabled
        ) == 0:
            errors.append({
                "code": (
                    "NO_ENABLED_LOG_SINK"
                ),
                "message": (
                    "At least one log sink must be enabled"
                ),
            })

        if len(
            enabled
        ) > 1:
            errors.append({
                "code": (
                    "MULTIPLE_ENABLED_LOG_SINKS"
                ),
                "message": (
                    "Current LoggingManager supports one configured memory sink"
                ),
            })

        if (
            config.minimum_level
            == "DEBUG"
        ):
            warnings.append({
                "code": (
                    "DEBUG_LOGGING_ENABLED"
                ),
                "message": (
                    "DEBUG logging can significantly increase retained log volume"
                ),
            })

        for sink in config.sinks:
            if (
                sink.max_records
                > 1000000
            ):
                warnings.append({
                    "code": (
                        "VERY_LARGE_LOG_BUFFER"
                    ),
                    "sink_id": (
                        sink.sink_id
                    ),
                    "message": (
                        "Configured in-memory log retention is unusually large"
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
            "enabled_sink_count": len(
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
