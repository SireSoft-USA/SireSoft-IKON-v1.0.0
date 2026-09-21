class GuardrailPolicyStatus:
    """
    Read-only description of the currently active transparent guardrail policy.

    This layer reports exactly what the handwritten rule system does. It does not
    present the rules as a learned classifier or comprehensive moderation model.
    """

    def __init__(
        self,
        engine,
    ):
        if engine is None:
            raise ValueError(
                "engine is required"
            )

        self.engine = engine

    def to_dict(
        self,
    ):
        patterns = (
            self.engine
            .input_guard
            .patterns
        )

        prompt_rules = []

        for phrase, code, severity in (
            patterns
            .prompt_injection_patterns
        ):
            prompt_rules.append({
                "phrase": phrase,
                "code": code,
                "category": (
                    "prompt_injection"
                ),
                "severity": severity,
            })

        secret_rules = []

        for phrase, code, severity in (
            patterns
            .secret_patterns
        ):
            secret_rules.append({
                "phrase": phrase,
                "code": code,
                "category": (
                    "secret_leakage"
                ),
                "severity": severity,
            })

        return {
            "policy_type": (
                "transparent_handwritten_guardrails"
            ),
            "learned_classifier": False,
            "limits": {
                "input_characters": (
                    self.engine
                    .input_guard
                    .max_characters
                ),
                "context_characters": (
                    self.engine
                    .context_guard
                    .max_characters
                ),
                "output_characters": (
                    self.engine
                    .output_guard
                    .max_characters
                ),
            },
            "input_policy": {
                "prompt_injection_language": (
                    "warn"
                ),
                "structural_integrity_failures": (
                    "block"
                ),
            },
            "context_policy": {
                "prompt_injection_language": (
                    "sanitize"
                ),
                "quarantine_open": (
                    self.engine
                    .context_guard
                    .OPEN_TAG
                ),
                "quarantine_close": (
                    self.engine
                    .context_guard
                    .CLOSE_TAG
                ),
                "structural_integrity_failures": (
                    "block"
                ),
            },
            "output_policy": {
                "high_severity_secret_or_disclosure": (
                    "block"
                ),
                "lower_severity_findings": (
                    "warn"
                ),
            },
            "prompt_injection_rule_count": (
                len(
                    prompt_rules
                )
            ),
            "secret_rule_count": (
                len(
                    secret_rules
                )
            ),
            "prompt_injection_rules": (
                prompt_rules
            ),
            "secret_rules": (
                secret_rules
            ),
        }
