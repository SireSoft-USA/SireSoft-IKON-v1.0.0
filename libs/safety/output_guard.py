class OutputGuard:
    """
    Post-generation output checks.

    Blocks likely secret leakage and internal-role disclosure markers. Empty or
    excessively long model output is treated as an integrity failure.
    """

    def __init__(
        self,
        patterns=None,
        max_characters=50000,
    ):
        if not isinstance(max_characters, int) or max_characters <= 0:
            raise ValueError("max_characters must be positive int")

        self.patterns = (
            SafetyPatterns()
            if patterns is None
            else patterns
        )

        self.max_characters = max_characters

    def inspect(
        self,
        text,
        decision_id="output-0",
    ):
        if not isinstance(text, str):
            raise TypeError("output text must be str")

        findings = []

        if text == "":
            findings.append(
                SafetyFinding(
                    code="EMPTY_OUTPUT",
                    category="output_integrity",
                    severity=3,
                    message="Generated output is empty",
                )
            )

        if len(text) > self.max_characters:
            findings.append(
                SafetyFinding(
                    code="OUTPUT_TOO_LONG",
                    category="resource_control",
                    severity=4,
                    message="Generated output exceeds configured limit",
                )
            )

        control_findings = (
            self.patterns.find_control_characters(
                text
            )
        )

        secret_findings = (
            self.patterns.find_secrets(
                text
            )
        )

        role_findings = []

        all_role_matches = (
            self.patterns.find_prompt_injection(
                text
            )
        )

        for finding in all_role_matches:
            if (
                finding.code.startswith(
                    "ROLE_TOKEN_"
                )
                or finding.code
                in (
                    "PROMPT_INJECTION_REVEAL_SYSTEM",
                    "PROMPT_INJECTION_SHOW_SYSTEM",
                )
            ):
                role_findings.append(
                    finding
                )

        findings.extend(
            control_findings
        )
        findings.extend(
            secret_findings
        )
        findings.extend(
            role_findings
        )

        should_block = False

        for finding in findings:
            if finding.severity >= 4:
                should_block = True
                break

            if finding.code == "CONTROL_CHARACTER":
                should_block = True
                break

        if should_block:
            action = "block"
            safe_text = None

        elif len(findings) > 0:
            action = "warn"
            safe_text = text

        else:
            action = "allow"
            safe_text = text

        return GuardrailDecision(
            decision_id=decision_id,
            phase="output",
            action=action,
            findings=findings,
            original_text=text,
            safe_text=safe_text,
        )
