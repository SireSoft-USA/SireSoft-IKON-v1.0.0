class FeatureFlagConfig:
    def __init__(
        self,
        flag_key,
        variants,
        default_variant,
        disabled_variant,
        rules=None,
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

        normalized_variants = {}

        for key in variants:
            if not isinstance(
                key,
                str,
            ) or key == "":
                raise ValueError(
                    "variant names must be non-empty strings"
                )

            normalized_variants[
                key
            ] = self._copy(
                variants[
                    key
                ]
            )

        if default_variant not in normalized_variants:
            raise ValueError(
                "default_variant must exist in variants"
            )

        if disabled_variant not in normalized_variants:
            raise ValueError(
                "disabled_variant must exist in variants"
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

        normalized_rules = []
        seen = {}

        for rule in rules:
            if not isinstance(
                rule,
                FeatureFlagRuleConfig,
            ):
                raise TypeError(
                    "rules entries must be FeatureFlagRuleConfig"
                )

            if rule.rule_id in seen:
                raise ValueError(
                    "duplicate rule_id: "
                    + rule.rule_id
                )

            if (
                rule.variant is not None
                and rule.variant
                not in normalized_variants
            ):
                raise ValueError(
                    "rule variant does not exist in flag variants"
                )

            if (
                rule.rollout_variant is not None
                and rule.rollout_variant
                not in normalized_variants
            ):
                raise ValueError(
                    "rollout variant does not exist in flag variants"
                )

            seen[
                rule.rule_id
            ] = True

            normalized_rules.append(
                rule
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
        self.variants = normalized_variants
        self.default_variant = (
            default_variant
        )
        self.disabled_variant = (
            disabled_variant
        )
        self.rules = normalized_rules
        self.enabled = bool(
            enabled
        )
        self.description = description
        self.metadata = self._copy(
            metadata
        )

    def to_dict(
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
                rule.to_dict()
                for rule
                in self.rules
            ],
        }

    def _copy(
        self,
        value,
    ):
        if isinstance(
            value,
            dict,
        ):
            return {
                key: self._copy(
                    value[
                        key
                    ]
                )
                for key
                in value
            }

        if isinstance(
            value,
            (list, tuple),
        ):
            return [
                self._copy(
                    item
                )
                for item
                in value
            ]

        return value
