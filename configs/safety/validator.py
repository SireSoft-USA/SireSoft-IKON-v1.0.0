class SafetyConfigValidator:
    def validate(self, config):
        if not isinstance(
            config,
            SafetyConfig,
        ):
            raise TypeError(
                "config must be SafetyConfig"
            )

        errors = []
        warnings = []

        enabled = config.enabled_rules()
        phrase_keys = {}

        for rule in enabled:
            key = (
                rule.category
                + "\x00"
                + rule.phrase.lower()
            )

            if key in phrase_keys:
                errors.append({
                    "code": (
                        "DUPLICATE_RULE_PHRASE"
                    ),
                    "rule_codes": [
                        phrase_keys[key],
                        rule.code,
                    ],
                    "message": (
                        "Two enabled rules match the same phrase in the same category"
                    ),
                })
            else:
                phrase_keys[key] = (
                    rule.code
                )

        if (
            config.replace_default_rules
            and len(enabled) == 0
        ):
            warnings.append({
                "code": (
                    "EMPTY_CUSTOM_RULE_CATALOG"
                ),
                "message": (
                    "Default rules are replaced but no custom rules are enabled"
                ),
            })

        if (
            config.limits.context_characters
            < config.limits.input_characters
        ):
            warnings.append({
                "code": (
                    "CONTEXT_LIMIT_BELOW_INPUT_LIMIT"
                ),
                "message": (
                    "Context character limit is smaller than input limit"
                ),
            })

        if (
            config.limits.output_characters
            > (
                config.limits.context_characters
                * 2
            )
        ):
            warnings.append({
                "code": (
                    "VERY_LARGE_OUTPUT_LIMIT"
                ),
                "message": (
                    "Output limit is more than twice the context limit"
                ),
            })

        return {
            "valid": len(errors) == 0,
            "error_count": len(errors),
            "warning_count": len(warnings),
            "errors": errors,
            "warnings": warnings,
            "enabled_custom_rule_count": (
                len(enabled)
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
