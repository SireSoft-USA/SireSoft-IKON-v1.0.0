class FeatureFlag:
    """
    Feature flag with named variants and ordered targeting rules.
    """

    def __init__(
        self,
        flag_key,
        variants,
        default_variant,
        disabled_variant,
        enabled=True,
        description="",
        metadata=None,
    ):
        if not isinstance(
            flag_key,
            str,
        ) or flag_key == "":
            raise ValueError(
                "flag_key must be non-empty str"
            )

        if not isinstance(
            variants,
            dict,
        ) or len(
            variants
        ) == 0:
            raise ValueError(
                "variants must be non-empty dict"
            )

        normalized = {}

        for key in variants:
            if not isinstance(
                key,
                str,
            ) or key == "":
                raise ValueError(
                    "variant names must be non-empty strings"
                )

            normalized[
                key
            ] = self._copy(
                variants[
                    key
                ]
            )

        if default_variant not in normalized:
            raise ValueError(
                "default_variant must exist in variants"
            )

        if disabled_variant not in normalized:
            raise ValueError(
                "disabled_variant must exist in variants"
            )

        if not isinstance(
            description,
            str,
        ):
            raise TypeError(
                "description must be str"
            )

        if metadata is None:
            metadata = {}

        if not isinstance(
            metadata,
            dict,
        ):
            raise TypeError(
                "metadata must be dict or None"
            )

        self.flag_key = flag_key
        self.variants = normalized
        self.default_variant = (
            default_variant
        )
        self.disabled_variant = (
            disabled_variant
        )
        self.enabled = bool(
            enabled
        )
        self.description = (
            description
        )
        self.metadata = self._copy(
            metadata
        )

        self._rules = {}
        self._rule_order = []

    def add_rule(
        self,
        rule,
    ):
        if not isinstance(
            rule,
            TargetingRule,
        ):
            raise TypeError(
                "rule must be TargetingRule"
            )

        if rule.rule_id in self._rules:
            raise ValueError(
                "duplicate rule_id: "
                + rule.rule_id
            )

        if (
            rule.variant is not None
            and rule.variant
            not in self.variants
        ):
            raise ValueError(
                "rule variant does not exist in flag"
            )

        if (
            rule.rollout_variant
            is not None
            and rule.rollout_variant
            not in self.variants
        ):
            raise ValueError(
                "rollout variant does not exist in flag"
            )

        self._rules[
            rule.rule_id
        ] = rule

        self._rule_order.append(
            rule.rule_id
        )

        return rule

    def remove_rule(
        self,
        rule_id,
    ):
        if rule_id not in self._rules:
            raise KeyError(
                "feature-flag rule not found: "
                + str(
                    rule_id
                )
            )

        rule = self._rules[
            rule_id
        ]

        del self._rules[
            rule_id
        ]

        self._rule_order = [
            existing
            for existing in self._rule_order
            if existing != rule_id
        ]

        return rule

    def rules(
        self,
    ):
        return [
            self._rules[
                rule_id
            ]
            for rule_id
            in self._rule_order
        ]

    def get_rule(
        self,
        rule_id,
    ):
        if rule_id not in self._rules:
            raise KeyError(
                "feature-flag rule not found: "
                + str(
                    rule_id
                )
            )

        return self._rules[
            rule_id
        ]

    def set_enabled(
        self,
        enabled,
    ):
        self.enabled = bool(
            enabled
        )

        return self

    def public_dict(
        self,
    ):
        return {
            "flag_key": self.flag_key,
            "variants": self._copy(
                self.variants
            ),
            "default_variant": (
                self.default_variant
            ),
            "disabled_variant": (
                self.disabled_variant
            ),
            "enabled": self.enabled,
            "description": (
                self.description
            ),
            "metadata": self._copy(
                self.metadata
            ),
            "rules": [
                rule.public_dict()
                for rule
                in self.rules()
            ],
        }

    @classmethod
    def from_dict(
        cls,
        value,
    ):
        if not isinstance(
            value,
            dict,
        ):
            raise TypeError(
                "feature flag state must be dict"
            )

        flag = cls(
            flag_key=value[
                "flag_key"
            ],
            variants=value[
                "variants"
            ],
            default_variant=value[
                "default_variant"
            ],
            disabled_variant=value[
                "disabled_variant"
            ],
            enabled=value.get(
                "enabled",
                True,
            ),
            description=value.get(
                "description",
                "",
            ),
            metadata=value.get(
                "metadata",
                {},
            ),
        )

        for rule_state in value.get(
            "rules",
            [],
        ):
            flag.add_rule(
                TargetingRule.from_dict(
                    rule_state
                )
            )

        return flag

    def _copy(
        self,
        value,
    ):
        if isinstance(
            value,
            dict,
        ):
            result = {}

            for key in value:
                result[
                    key
                ] = self._copy(
                    value[
                        key
                    ]
                )

            return result

        if isinstance(
            value,
            list,
        ):
            return [
                self._copy(
                    item
                )
                for item in value
            ]

        if isinstance(
            value,
            tuple,
        ):
            return [
                self._copy(
                    item
                )
                for item in value
            ]

        return value
