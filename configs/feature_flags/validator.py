class FeatureFlagsConfigValidator:
    def validate(
        self,
        config,
    ):
        if not isinstance(
            config,
            FeatureFlagsConfig,
        ):
            raise TypeError(
                "config must be FeatureFlagsConfig"
            )

        errors = []
        warnings = []

        enabled_flags = 0

        for flag in config.flags:
            if flag.enabled:
                enabled_flags += 1

            if len(
                flag.variants
            ) == 1:
                warnings.append({
                    "code": (
                        "SINGLE_VARIANT_FLAG"
                    ),
                    "flag_key": (
                        flag.flag_key
                    ),
                    "message": (
                        "Feature flag has only one variant"
                    ),
                })

            rollout_rules = 0

            for rule in flag.rules:
                if (
                    rule.rollout_basis_points
                    is not None
                ):
                    rollout_rules += 1

                    if (
                        rule.rollout_basis_points
                        == 0
                    ):
                        warnings.append({
                            "code": (
                                "ZERO_PERCENT_ROLLOUT"
                            ),
                            "flag_key": (
                                flag.flag_key
                            ),
                            "rule_id": (
                                rule.rule_id
                            ),
                            "message": (
                                "Rollout rule never selects its rollout variant"
                            ),
                        })

                    if (
                        rule.rollout_basis_points
                        == 10000
                    ):
                        warnings.append({
                            "code": (
                                "FULL_PERCENT_ROLLOUT"
                            ),
                            "flag_key": (
                                flag.flag_key
                            ),
                            "rule_id": (
                                rule.rule_id
                            ),
                            "message": (
                                "Rollout rule always selects its rollout variant when conditions match"
                            ),
                        })

            if rollout_rules > 3:
                warnings.append({
                    "code": (
                        "MANY_ROLLOUT_RULES"
                    ),
                    "flag_key": (
                        flag.flag_key
                    ),
                    "message": (
                        "Feature flag has many rollout rules"
                    ),
                })

        if enabled_flags == 0:
            warnings.append({
                "code": (
                    "NO_ENABLED_FEATURE_FLAGS"
                ),
                "message": (
                    "No feature flags are enabled"
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
            "enabled_flag_count": (
                enabled_flags
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
