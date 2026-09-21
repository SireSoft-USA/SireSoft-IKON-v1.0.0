class AuthConfigValidator:
    def validate(
        self,
        config,
        gateway_catalog=None,
    ):
        if not isinstance(
            config,
            AuthConfig,
        ):
            raise TypeError(
                "config must be AuthConfig"
            )

        errors = []
        warnings = []

        permission_universe = {}

        for role in config.roles:
            for permission in role.permissions:
                permission_universe[
                    permission
                ] = True

        if "*" in permission_universe:
            warnings.append({
                "code": (
                    "WILDCARD_PERMISSION_PRESENT"
                ),
                "message": (
                    "At least one configured role has wildcard permission"
                ),
            })

        known_route_keys = None

        if gateway_catalog is not None:
            if not isinstance(
                gateway_catalog,
                GatewayConfigCatalog,
            ):
                raise TypeError(
                    "gateway_catalog must be GatewayConfigCatalog or None"
                )

            known_route_keys = {}

            for route in gateway_catalog.routes():
                known_route_keys[
                    route.key()
                ] = route

        for route_key in config.permission_by_route:
            permission = (
                config.permission_by_route[
                    route_key
                ]
            )

            if (
                permission
                not in permission_universe
                and "*"
                not in permission_universe
            ):
                warnings.append({
                    "code": (
                        "UNASSIGNED_PERMISSION"
                    ),
                    "route": route_key,
                    "permission": permission,
                    "message": (
                        "Route permission is not assigned to any configured role"
                    ),
                })

            if (
                known_route_keys is not None
                and route_key
                not in known_route_keys
            ):
                errors.append({
                    "code": (
                        "UNKNOWN_GATEWAY_ROUTE"
                    ),
                    "route": route_key,
                    "message": (
                        "Authentication permission references an unknown gateway route"
                    ),
                })

            elif (
                known_route_keys is not None
                and not known_route_keys[
                    route_key
                ].auth_required
            ):
                warnings.append({
                    "code": (
                        "PERMISSION_ON_PUBLIC_ROUTE"
                    ),
                    "route": route_key,
                    "message": (
                        "Permission is configured for a route that does not require authentication"
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
        config,
        gateway_catalog=None,
    ):
        result = self.validate(
            config,
            gateway_catalog=(
                gateway_catalog
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
