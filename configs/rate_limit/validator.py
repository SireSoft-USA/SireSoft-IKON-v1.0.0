class RateLimitConfigValidator:
    def validate(
        self,
        config,
        gateway_catalog=None,
    ):
        if not isinstance(
            config,
            RateLimitConfig,
        ):
            raise TypeError(
                "config must be RateLimitConfig"
            )

        if (
            gateway_catalog is not None
            and not isinstance(
                gateway_catalog,
                GatewayConfigCatalog,
            )
        ):
            raise TypeError(
                "gateway_catalog must be GatewayConfigCatalog or None"
            )

        errors = []
        warnings = []

        policy_map = (
            config.policy_map()
        )

        if (
            config.default_policy_id
            is not None
            and config.default_policy_id
            not in policy_map
        ):
            errors.append({
                "code": (
                    "UNKNOWN_DEFAULT_POLICY"
                ),
                "policy_id": (
                    config
                    .default_policy_id
                ),
                "message": (
                    "Default rate-limit policy is not configured"
                ),
            })

        known_route_keys = None

        if gateway_catalog is not None:
            known_route_keys = {}

            for route in gateway_catalog.routes():
                known_route_keys[
                    route.key()
                ] = route

        referenced = {}

        if config.default_policy_id is not None:
            referenced[
                config.default_policy_id
            ] = True

        for route_key in config.policy_by_route:
            policy_id = (
                config.policy_by_route[
                    route_key
                ]
            )

            if policy_id not in policy_map:
                errors.append({
                    "code": (
                        "UNKNOWN_ROUTE_POLICY"
                    ),
                    "route": route_key,
                    "policy_id": (
                        policy_id
                    ),
                    "message": (
                        "Route references an unknown rate-limit policy"
                    ),
                })

            else:
                referenced[
                    policy_id
                ] = True

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
                        "Rate-limit mapping references an unknown gateway route"
                    ),
                })

        for policy in config.policies:
            if (
                policy.policy_id
                not in referenced
            ):
                warnings.append({
                    "code": (
                        "UNREFERENCED_POLICY"
                    ),
                    "policy_id": (
                        policy.policy_id
                    ),
                    "message": (
                        "Rate-limit policy is configured but not referenced"
                    ),
                })

            if not policy.enabled:
                warnings.append({
                    "code": (
                        "DISABLED_POLICY"
                    ),
                    "policy_id": (
                        policy.policy_id
                    ),
                    "message": (
                        "Rate-limit policy is disabled"
                    ),
                })

        if (
            config.default_policy_id
            is None
            and len(
                config.policy_by_route
            ) == 0
        ):
            warnings.append({
                "code": (
                    "NO_ACTIVE_MAPPING"
                ),
                "message": (
                    "No default or route-specific rate-limit policy is mapped"
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
