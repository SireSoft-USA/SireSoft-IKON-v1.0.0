class ServiceDiscoveryConfigValidator:
    def validate(self, config):
        if not isinstance(
            config,
            ServiceDiscoveryConfig,
        ):
            raise TypeError(
                "config must be ServiceDiscoveryConfig"
            )

        errors = []
        warnings = []

        enabled = config.enabled_instances()

        local_count = 0
        service_counts = {}

        for instance in enabled:
            service_counts[
                instance.service_name
            ] = (
                service_counts.get(
                    instance.service_name,
                    0,
                )
                + 1
            )

            if instance.local():
                local_count += 1

                if not config.attach_load_balancer:
                    errors.append({
                        "code": (
                            "LOCAL_INSTANCE_WITHOUT_LOAD_BALANCER"
                        ),
                        "instance_id": (
                            instance.instance_id
                        ),
                        "message": (
                            "Local discovered instances require load-balancer attachment"
                        ),
                    })

            if (
                instance.endpoint.startswith(
                    "local://"
                )
                and not instance.local()
            ):
                warnings.append({
                    "code": (
                        "LOCAL_ENDPOINT_WITHOUT_HANDLER_KEY"
                    ),
                    "instance_id": (
                        instance.instance_id
                    ),
                    "message": (
                        "local:// endpoint is declared without local_handler_key"
                    ),
                })

            if instance.lease_seconds < 5:
                warnings.append({
                    "code": (
                        "VERY_SHORT_DISCOVERY_LEASE"
                    ),
                    "instance_id": (
                        instance.instance_id
                    ),
                    "message": (
                        "Very short lease may mark instances stale too aggressively"
                    ),
                })

        for service_name in service_counts:
            if service_counts[
                service_name
            ] == 1:
                warnings.append({
                    "code": (
                        "SINGLE_DISCOVERY_INSTANCE"
                    ),
                    "service_name": (
                        service_name
                    ),
                    "message": (
                        "Service has no discovery-level redundancy"
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
            "local_instance_count": local_count,
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
