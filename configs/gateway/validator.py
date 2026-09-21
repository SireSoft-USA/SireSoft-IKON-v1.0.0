class GatewayConfigValidator:
    """
    Cross-validates gateway configuration against service configuration.
    """

    ALLOWED_METHODS = (
        "GET",
        "POST",
        "PUT",
        "PATCH",
        "DELETE",
        "HEAD",
        "OPTIONS",
    )

    def validate(
        self,
        gateway_catalog,
        service_catalog=None,
    ):
        if not isinstance(
            gateway_catalog,
            GatewayConfigCatalog,
        ):
            raise TypeError(
                "gateway_catalog must be GatewayConfigCatalog"
            )

        if (
            service_catalog is not None
            and not isinstance(
                service_catalog,
                ServiceConfigCatalog,
            )
        ):
            raise TypeError(
                "service_catalog must be ServiceConfigCatalog or None"
            )

        errors = []
        warnings = []

        enabled = (
            gateway_catalog
            .routes(
                enabled_only=True
            )
        )

        if len(
            enabled
        ) == 0:
            warnings.append({
                "code": (
                    "NO_ENABLED_ROUTES"
                ),
                "message": (
                    "No enabled gateway routes are configured"
                ),
            })

        known_services = {}

        if service_catalog is not None:
            for service_name in (
                service_catalog.services()
            ):
                known_services[
                    service_name
                ] = True

        for route in gateway_catalog.routes():
            if (
                route.method
                not in self.ALLOWED_METHODS
            ):
                errors.append({
                    "code": (
                        "UNSUPPORTED_METHOD"
                    ),
                    "route": route.key(),
                    "message": (
                        "Unsupported HTTP method"
                    ),
                })

            if (
                route.path != "/"
                and route.path.endswith(
                    "/"
                )
            ):
                warnings.append({
                    "code": (
                        "TRAILING_SLASH"
                    ),
                    "route": route.key(),
                    "message": (
                        "Route path has trailing slash"
                    ),
                })

            if (
                service_catalog is not None
                and route.service
                not in known_services
                and route.service
                != "runtime_control"
            ):
                errors.append({
                    "code": (
                        "UNKNOWN_TARGET_SERVICE"
                    ),
                    "route": route.key(),
                    "service": (
                        route.service
                    ),
                    "message": (
                        "Gateway route targets an unconfigured service"
                    ),
                })

            if (
                route.enabled
                and route.max_payload_bytes
                is None
                and route.method
                in (
                    "POST",
                    "PUT",
                    "PATCH",
                )
            ):
                warnings.append({
                    "code": (
                        "NO_PAYLOAD_LIMIT"
                    ),
                    "route": route.key(),
                    "message": (
                        "Body-bearing route has no configured payload limit"
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
        }

    def require_valid(
        self,
        gateway_catalog,
        service_catalog=None,
    ):
        result = self.validate(
            gateway_catalog,
            service_catalog=(
                service_catalog
            ),
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
