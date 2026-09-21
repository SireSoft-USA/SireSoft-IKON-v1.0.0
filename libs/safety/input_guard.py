class InputGuard:
    """
    Validates user/query input before retrieval or generation.

    Input prompt-injection language is surfaced as a warning rather than blindly
    blocked because users can legitimately ask about prompt injection itself.
    Structural corruption and excessive input size can be blocked.
    """

    def __init__(
        self,
        patterns=None,
        max_characters=20000,
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
        decision_id="input-0",
    ):
        if not isinstance(text, str):
            raise TypeError("input text must be str")

        findings = []

        if text.strip() == "":
            findings.append(
                SafetyFinding(
                    code="EMPTY_INPUT",
                    category="input_integrity",
                    severity=4,
                    message="Input is empty",
                )
            )

        if len(text) > self.max_characters:
            findings.append(
                SafetyFinding(
                    code="INPUT_TOO_LONG",
                    category="resource_control",
                    severity=4,
                    message=(
                        "Input exceeds configured character limit"
                    ),
                )
            )

        findings.extend(
            self.patterns.find_control_characters(
                text
            )
        )

        injection = (
            self.patterns.find_prompt_injection(
                text
            )
        )

        # User input injection-like language is informational/warning context,
        # not automatically a block. Preserve original severities but decision
        # policy below distinguishes structural blockers from content warnings.
        findings.extend(
            injection
        )

        block_codes = {
            "EMPTY_INPUT": True,
            "INPUT_TOO_LONG": True,
            "CONTROL_CHARACTER": True,
        }

        should_block = False

        for finding in findings:
            if finding.code in block_codes:
                should_block = True
                break

        if should_block:
            action = "block"
        elif len(findings) > 0:
            action = "warn"
        else:
            action = "allow"

        return GuardrailDecision(
            decision_id=decision_id,
            phase="input",
            action=action,
            findings=findings,
            original_text=text,
            safe_text=text if action != "block" else None,
        )
