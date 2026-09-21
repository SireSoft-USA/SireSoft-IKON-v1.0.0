class SecretsConfigValidator:
    def validate(
        self,
        config,
    ):
        if not isinstance(
            config,
            SecretsConfig,
        ):
            raise TypeError(
                "config must be SecretsConfig"
            )

        errors = []
        warnings = []

        enabled_count = 0

        for secret in config.secrets:
            if secret.enabled:
                enabled_count += 1

            policy = secret.policy

            if (
                len(
                    policy.admins
                )
                == 0
            ):
                warnings.append({
                    "code": (
                        "NO_CONFIGURED_ADMIN"
                    ),
                    "secret_id": (
                        secret.secret_id
                    ),
                    "message": (
                        "No explicit admin configured; bootstrap actor will become admin"
                    ),
                })

            if "*" in policy.admins:
                errors.append({
                    "code": (
                        "WILDCARD_ADMIN_FORBIDDEN"
                    ),
                    "secret_id": (
                        secret.secret_id
                    ),
                    "message": (
                        "Wildcard secret administrators are not allowed by configuration policy"
                    ),
                })

            if "*" in policy.writers:
                warnings.append({
                    "code": (
                        "WILDCARD_WRITER"
                    ),
                    "secret_id": (
                        secret.secret_id
                    ),
                    "message": (
                        "Wildcard secret writer grants rotation access to every principal"
                    ),
                })

            if "*" in policy.readers:
                warnings.append({
                    "code": (
                        "WILDCARD_READER"
                    ),
                    "secret_id": (
                        secret.secret_id
                    ),
                    "message": (
                        "Wildcard secret reader grants read access to every principal"
                    ),
                })

        if enabled_count == 0:
            warnings.append({
                "code": (
                    "NO_ENABLED_SECRETS"
                ),
                "message": (
                    "No configured secrets are enabled"
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
            "enabled_secret_count": (
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
