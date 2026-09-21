class SafetyConfig:
    def __init__(
        self,
        limits=None,
        rules=None,
        replace_default_rules=False,
        metadata=None,
    ):
        if limits is None:
            limits = SafetyLimitsConfig()

        if not isinstance(
            limits,
            SafetyLimitsConfig,
        ):
            raise TypeError(
                "limits must be SafetyLimitsConfig"
            )

        if rules is None:
            rules = []

        if not isinstance(
            rules,
            (list, tuple),
        ):
            raise TypeError(
                "rules must be list/tuple or None"
            )

        normalized = []
        seen_codes = {}

        for rule in rules:
            if not isinstance(
                rule,
                SafetyRuleConfig,
            ):
                raise TypeError(
                    "rules entries must be SafetyRuleConfig"
                )

            if rule.code in seen_codes:
                raise ValueError(
                    "duplicate safety rule code: "
                    + rule.code
                )

            seen_codes[rule.code] = True
            normalized.append(rule)

        if metadata is None:
            metadata = {}

        if not isinstance(metadata, dict):
            raise TypeError(
                "metadata must be dict or None"
            )

        self.limits = limits
        self.rules = normalized
        self.replace_default_rules = bool(
            replace_default_rules
        )
        self.metadata = self._copy(metadata)

    def enabled_rules(self):
        return [
            rule
            for rule in self.rules
            if rule.enabled
        ]

    def to_dict(self):
        return {
            "limits": self.limits.to_dict(),
            "rules": [
                rule.to_dict()
                for rule in self.rules
            ],
            "replace_default_rules": (
                self.replace_default_rules
            ),
            "metadata": self._copy(
                self.metadata
            ),
        }

    def _copy(self, value):
        if isinstance(value, dict):
            return {
                key: self._copy(value[key])
                for key in value
            }

        if isinstance(value, (list, tuple)):
            return [
                self._copy(item)
                for item in value
            ]

        return value
