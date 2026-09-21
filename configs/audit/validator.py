class AuditConfigValidator:
    def validate(
        self,
        config,
    ):
        if not isinstance(
            config,
            AuditConfig,
        ):
            raise TypeError(
                "config must be AuditConfig"
            )

        errors = []
        warnings = []

        if (
            config.policy
            .expected_integrity_scheme
            != "fnv1a64_hash_chain"
        ):
            errors.append({
                "code": (
                    "UNSUPPORTED_AUDIT_INTEGRITY_SCHEME"
                ),
                "message": (
                    "Current audit runtime implements fnv1a64_hash_chain"
                ),
            })

        if not (
            config.policy
            .require_metadata_sanitization
        ):
            warnings.append({
                "code": (
                    "AUDIT_SANITIZATION_EXPECTATION_DISABLED"
                ),
                "message": (
                    "Runtime still sanitizes common secret-bearing metadata keys"
                ),
            })

        if not (
            config.policy
            .require_append_only
        ):
            warnings.append({
                "code": (
                    "AUDIT_APPEND_ONLY_EXPECTATION_DISABLED"
                ),
                "message": (
                    "Runtime API remains append-only and exposes no delete/clear operation"
                ),
            })

        if (
            config.persistence
            .state_path
            is not None
            and not config
            .persistence
            .load_state_on_start
        ):
            warnings.append({
                "code": (
                    "AUDIT_STATE_NOT_AUTO_LOADED"
                ),
                "message": (
                    "state_path is configured but startup load is disabled"
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
