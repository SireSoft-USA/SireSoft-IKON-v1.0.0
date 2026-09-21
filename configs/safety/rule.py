class SafetyRuleConfig:
    CATEGORIES = (
        "prompt_injection",
        "secret_leakage",
    )

    def __init__(
        self,
        phrase,
        code,
        category,
        severity,
        enabled=True,
    ):
        if not isinstance(phrase, str) or phrase == "":
            raise ValueError(
                "phrase must be non-empty str"
            )

        if not isinstance(code, str) or code == "":
            raise ValueError(
                "code must be non-empty str"
            )

        if category not in self.CATEGORIES:
            raise ValueError(
                "unsupported safety rule category"
            )

        if (
            not isinstance(severity, int)
            or severity < 1
            or severity > 4
        ):
            raise ValueError(
                "severity must be int in range 1..4"
            )

        self.phrase = phrase
        self.code = code
        self.category = category
        self.severity = severity
        self.enabled = bool(enabled)

    def to_dict(self):
        return {
            "phrase": self.phrase,
            "code": self.code,
            "category": self.category,
            "severity": self.severity,
            "enabled": self.enabled,
        }
