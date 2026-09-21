class SafetyPatterns:
    """
    Handwritten pattern catalog and matcher.

    Patterns are intentionally transparent and inspectable. This is a rule
    system, not a claim of learned safety classification.
    """

    def __init__(self):
        self.prompt_injection_patterns = [
            (
                "ignore previous instructions",
                "PROMPT_INJECTION_IGNORE_PREVIOUS",
                4,
            ),
            (
                "ignore all previous instructions",
                "PROMPT_INJECTION_IGNORE_ALL",
                4,
            ),
            (
                "disregard previous instructions",
                "PROMPT_INJECTION_DISREGARD",
                4,
            ),
            (
                "override system instructions",
                "PROMPT_INJECTION_OVERRIDE_SYSTEM",
                4,
            ),
            (
                "reveal the system prompt",
                "PROMPT_INJECTION_REVEAL_SYSTEM",
                4,
            ),
            (
                "show me the system prompt",
                "PROMPT_INJECTION_SHOW_SYSTEM",
                4,
            ),
            (
                "developer message",
                "PROMPT_INJECTION_DEVELOPER_MESSAGE",
                3,
            ),
            (
                "system message",
                "PROMPT_INJECTION_SYSTEM_MESSAGE",
                3,
            ),
            (
                "<system>",
                "ROLE_TOKEN_SYSTEM",
                3,
            ),
            (
                "</system>",
                "ROLE_TOKEN_SYSTEM_CLOSE",
                3,
            ),
            (
                "<developer>",
                "ROLE_TOKEN_DEVELOPER",
                3,
            ),
            (
                "<assistant>",
                "ROLE_TOKEN_ASSISTANT",
                2,
            ),
        ]

        self.secret_patterns = [
            (
                "api_key=",
                "SECRET_API_KEY_ASSIGNMENT",
                4,
            ),
            (
                "api-key:",
                "SECRET_API_KEY_LABEL",
                4,
            ),
            (
                "password=",
                "SECRET_PASSWORD_ASSIGNMENT",
                4,
            ),
            (
                "password:",
                "SECRET_PASSWORD_LABEL",
                3,
            ),
            (
                "authorization: bearer ",
                "SECRET_BEARER_TOKEN",
                4,
            ),
            (
                "private_key",
                "SECRET_PRIVATE_KEY_MARKER",
                4,
            ),
        ]

    def find_prompt_injection(self, text):
        return self._find(
            text,
            self.prompt_injection_patterns,
            category="prompt_injection",
        )

    def find_secrets(self, text):
        return self._find(
            text,
            self.secret_patterns,
            category="secret_leakage",
        )

    def find_control_characters(self, text):
        if not isinstance(text, str):
            raise TypeError("text must be str")

        findings = []
        index = 0

        while index < len(text):
            code = ord(text[index])

            # Permit normal whitespace controls only.
            if (
                code < 32
                and text[index] not in ("\n", "\r", "\t")
            ):
                findings.append(
                    SafetyFinding(
                        code="CONTROL_CHARACTER",
                        category="input_integrity",
                        severity=3,
                        message=(
                            "Unexpected control character in text"
                        ),
                        start=index,
                        end=index + 1,
                        evidence=repr(text[index]),
                    )
                )

            index += 1

        return findings

    def _find(
        self,
        text,
        patterns,
        category,
    ):
        if not isinstance(text, str):
            raise TypeError("text must be str")

        lowered = text.lower()
        findings = []

        for phrase, code, severity in patterns:
            start = 0

            while True:
                index = lowered.find(
                    phrase,
                    start,
                )

                if index < 0:
                    break

                findings.append(
                    SafetyFinding(
                        code=code,
                        category=category,
                        severity=severity,
                        message=(
                            "Matched guardrail pattern: "
                            + phrase
                        ),
                        start=index,
                        end=index + len(phrase),
                        evidence=text[
                            index:index + len(phrase)
                        ],
                    )
                )

                start = (
                    index
                    + len(phrase)
                )

        findings.sort(
            key=lambda finding: (
                (
                    finding.start
                    if finding.start is not None
                    else 10 ** 12
                ),
                -finding.severity,
                finding.code,
            )
        )

        return findings
