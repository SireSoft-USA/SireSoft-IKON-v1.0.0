class ModelRegistryConfigValidator:
    def validate(
        self,
        config,
    ):
        if not isinstance(
            config,
            ModelRegistryConfig,
        ):
            raise TypeError(
                "config must be ModelRegistryConfig"
            )

        errors = []
        warnings = []

        promoted_by_model = {}
        enabled_count = 0

        for item in config.versions:
            if item.enabled:
                enabled_count += 1

            if item.promote:
                if (
                    item.model_id
                    in promoted_by_model
                ):
                    errors.append({
                        "code": (
                            "MULTIPLE_PROMOTED_VERSIONS"
                        ),
                        "model_id": (
                            item.model_id
                        ),
                        "versions": [
                            promoted_by_model[
                                item.model_id
                            ],
                            item.version,
                        ],
                        "message": (
                            "Only one configured version can be promoted per model"
                        ),
                    })

                else:
                    promoted_by_model[
                        item.model_id
                    ] = item.version

            if (
                item.verify
                and not item.enabled
            ):
                warnings.append({
                    "code": (
                        "VERIFY_DISABLED_VERSION"
                    ),
                    "model_id": (
                        item.model_id
                    ),
                    "version": (
                        item.version
                    ),
                    "message": (
                        "Verification flag has no startup effect on disabled version"
                    ),
                })

            if (
                not item.stage
                and not item.promote
                and item.enabled
            ):
                warnings.append({
                    "code": (
                        "REGISTER_ONLY_VERSION"
                    ),
                    "model_id": (
                        item.model_id
                    ),
                    "version": (
                        item.version
                    ),
                    "message": (
                        "Version will be registered without staging or promotion"
                    ),
                })

        if enabled_count == 0:
            errors.append({
                "code": (
                    "NO_ENABLED_MODEL_VERSIONS"
                ),
                "message": (
                    "At least one model version must be enabled"
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
            "enabled_version_count": (
                enabled_count
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
