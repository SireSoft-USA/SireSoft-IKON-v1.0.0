class MonitoringConfigValidator:
    def validate(
        self,
        config,
    ):
        if not isinstance(
            config,
            MonitoringConfig,
        ):
            raise TypeError(
                "config must be MonitoringConfig"
            )

        errors = []
        warnings = []

        enabled = (
            config.enabled_probes()
        )

        if (
            len(enabled) == 0
            and not config
            .attach_load_balancer
        ):
            warnings.append({
                "code": (
                    "NO_ACTIVE_MONITORING_INPUTS"
                ),
                "message": (
                    "Monitoring has no enabled probes and no load balancer"
                ),
            })

        service_probe_counts = {}

        for probe in enabled:
            service_probe_counts[
                probe.service_name
            ] = (
                service_probe_counts.get(
                    probe.service_name,
                    0,
                )
                + 1
            )

            if (
                len(
                    probe.readiness_path
                )
                == 0
            ):
                warnings.append({
                    "code": (
                        "PROBE_WITHOUT_READINESS_PATH"
                    ),
                    "probe_id": (
                        probe.probe_id
                    ),
                    "message": (
                        "Probe only checks protocol success, not readiness"
                    ),
                })

        for service_name in (
            service_probe_counts
        ):
            if (
                service_probe_counts[
                    service_name
                ]
                > 3
            ):
                warnings.append({
                    "code": (
                        "MANY_PROBES_FOR_SERVICE"
                    ),
                    "service_name": (
                        service_name
                    ),
                    "message": (
                        "More than three enabled probes target one service"
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
            "enabled_probe_count": len(
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
            ][0]

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
