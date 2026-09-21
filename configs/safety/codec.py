class SafetyConfigCodec:
    def __init__(
        self,
        parser=None,
    ):
        self.parser = (
            JSONParser()
            if parser is None
            else parser
        )

    def decode_text(self, text):
        if not isinstance(text, str):
            raise TypeError(
                "safety config text must be str"
            )

        return self.from_dict(
            self.parser.parse(text)
        )

    def from_dict(self, value):
        if not isinstance(value, dict):
            raise ValueError(
                "safety config root must be object"
            )

        raw_limits = value.get(
            "limits",
            {},
        )

        if not isinstance(
            raw_limits,
            dict,
        ):
            raise ValueError(
                "limits must be object"
            )

        raw_rules = value.get(
            "rules",
            [],
        )

        if not isinstance(
            raw_rules,
            list,
        ):
            raise ValueError(
                "rules must be list"
            )

        rules = []

        for raw in raw_rules:
            if not isinstance(raw, dict):
                raise ValueError(
                    "safety rule must be object"
                )

            rules.append(
                SafetyRuleConfig(
                    phrase=raw.get("phrase"),
                    code=raw.get("code"),
                    category=raw.get(
                        "category"
                    ),
                    severity=raw.get(
                        "severity"
                    ),
                    enabled=raw.get(
                        "enabled",
                        True,
                    ),
                )
            )

        return SafetyConfig(
            limits=SafetyLimitsConfig(
                input_characters=raw_limits.get(
                    "input_characters",
                    20000,
                ),
                context_characters=raw_limits.get(
                    "context_characters",
                    100000,
                ),
                output_characters=raw_limits.get(
                    "output_characters",
                    50000,
                ),
            ),
            rules=rules,
            replace_default_rules=value.get(
                "replace_default_rules",
                False,
            ),
            metadata=value.get(
                "metadata",
                {},
            ),
        )
