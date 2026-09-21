class LoadBalancerConfigValidator:
    def validate(self, config):
        if not isinstance(
            config,
            LoadBalancerConfig,
        ):
            raise TypeError(
                "config must be LoadBalancerConfig"
            )

        errors = []
        warnings = []

        enabled = config.enabled_instances()
        service_counts = {}

        for item in enabled:
            service_counts[
                item.service_name
            ] = (
                service_counts.get(
                    item.service_name,
                    0,
                )
                + 1
            )

            if not item.healthy:
                warnings.append({
                    "code": (
                        "INSTANCE_STARTS_UNHEALTHY"
                    ),
                    "instance_id": (
                        item.instance_id
                    ),
                    "message": (
                        "Instance will be registered unavailable until runtime recovery marks it healthy"
                    ),
                })

            if not item.accepting_requests:
                warnings.append({
                    "code": (
                        "INSTANCE_STARTS_PAUSED"
                    ),
                    "instance_id": (
                        item.instance_id
                    ),
                    "message": (
                        "Instance will be registered but initially paused"
                    ),
                })

        if config.require_service_redundancy:
            for service_name in service_counts:
                if service_counts[
                    service_name
                ] < 2:
                    errors.append({
                        "code": (
                            "SERVICE_REDUNDANCY_REQUIRED"
                        ),
                        "service_name": (
                            service_name
                        ),
                        "message": (
                            "Service has fewer than two enabled instances"
                        ),
                    })

        if (
            len(enabled) > 0
            and config.max_attempts
            > len(enabled)
        ):
            warnings.append({
                "code": (
                    "MAX_ATTEMPTS_EXCEEDS_TOTAL_INSTANCES"
                ),
                "message": (
                    "Global retry attempt limit exceeds total enabled instances"
                ),
            })

        return {
            "valid": len(errors) == 0,
            "error_count": len(errors),
            "warning_count": len(warnings),
            "errors": errors,
            "warnings": warnings,
            "enabled_instance_count": len(
                enabled
            ),
            "service_count": len(
                service_counts
            ),
        }

    def require_valid(self, config):
        result = self.validate(config)

        if not result["valid"]:
            first = result["errors"][0]
            raise ValueError(
                first["code"]
                + ": "
                + first["message"]
            )

        return result
