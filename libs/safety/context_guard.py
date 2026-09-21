class ContextGuard:
    """
    Inspects retrieved/untrusted context for prompt-injection instructions.

    Suspicious lines are quarantined instead of deleted. The original source is
    retained in GuardrailDecision.original_text for auditability.
    """

    OPEN_TAG = "[[UNTRUSTED_INSTRUCTION]]"
    CLOSE_TAG = "[[/UNTRUSTED_INSTRUCTION]]"

    def __init__(
        self,
        patterns=None,
        max_characters=100000,
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
        decision_id="context-0",
    ):
        if not isinstance(text, str):
            raise TypeError("context text must be str")

        findings = []

        if len(text) > self.max_characters:
            findings.append(
                SafetyFinding(
                    code="CONTEXT_TOO_LONG",
                    category="resource_control",
                    severity=4,
                    message=(
                        "Retrieved context exceeds configured limit"
                    ),
                )
            )

        findings.extend(
            self.patterns.find_control_characters(
                text
            )
        )

        injection_findings = (
            self.patterns.find_prompt_injection(
                text
            )
        )

        findings.extend(
            injection_findings
        )

        structural_block = False

        for finding in findings:
            if finding.code in (
                "CONTEXT_TOO_LONG",
                "CONTROL_CHARACTER",
            ):
                structural_block = True
                break

        if structural_block:
            return GuardrailDecision(
                decision_id=decision_id,
                phase="context",
                action="block",
                findings=findings,
                original_text=text,
                safe_text=None,
            )

        if len(injection_findings) == 0:
            return GuardrailDecision(
                decision_id=decision_id,
                phase="context",
                action="allow",
                findings=findings,
                original_text=text,
                safe_text=text,
            )

        safe_text = self._quarantine_lines(
            text,
            injection_findings,
        )

        return GuardrailDecision(
            decision_id=decision_id,
            phase="context",
            action="sanitize",
            findings=findings,
            original_text=text,
            safe_text=safe_text,
        )

    def _quarantine_lines(
        self,
        text,
        findings,
    ):
        lines = self._split_lines_with_offsets(
            text
        )

        output = []

        for line_text, start, end in lines:
            suspicious = False

            for finding in findings:
                if (
                    finding.start is not None
                    and finding.end is not None
                    and finding.start < end
                    and finding.end > start
                ):
                    suspicious = True
                    break

            if suspicious:
                output.append(
                    self.OPEN_TAG
                    + line_text
                    + self.CLOSE_TAG
                )
            else:
                output.append(
                    line_text
                )

        return "".join(output)

    def _split_lines_with_offsets(
        self,
        text,
    ):
        result = []
        start = 0
        index = 0

        while index < len(text):
            if text[index] == "\n":
                end = index + 1

                result.append(
                    (
                        text[start:end],
                        start,
                        end,
                    )
                )

                start = end

            index += 1

        if start < len(text):
            result.append(
                (
                    text[start:],
                    start,
                    len(text),
                )
            )

        if len(text) == 0:
            result.append(
                ("", 0, 0)
            )

        return result
