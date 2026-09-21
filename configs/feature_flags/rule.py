class FeatureFlagRuleConfig:
    def __init__(
        self,
        rule_id,
        conditions=None,
        variant=None,
        rollout_basis_points=None,
        rollout_variant=None,
        salt="",
        enabled=True,
        metadata=None,
    ):
        if not isinstance(
            rule_id,
            str,
        ) or rule_id == "":
            raise ValueError(
                "rule_id must be non-empty str"
            )

        if conditions is None:
            conditions = []

        if not isinstance(
            conditions,
            list,
        ):
            raise TypeError(
                "conditions must be list or None"
            )

        normalized_conditions = []

        for condition in conditions:
            if not isinstance(
                condition,
                dict,
            ):
                raise TypeError(
                    "each condition must be dict"
                )

            attribute = condition.get(
                "attribute"
            )
            operator = condition.get(
                "operator"
            )

            if not isinstance(
                attribute,
                str,
            ) or attribute == "":
                raise ValueError(
                    "condition attribute must be non-empty str"
                )

            if operator not in TargetingRule.OPERATORS:
                raise ValueError(
                    "unsupported targeting operator"
                )

            normalized_conditions.append({
                "attribute": attribute,
                "operator": operator,
                "value": self._copy(
                    condition.get(
                        "value"
                    )
                ),
            })

        if variant is not None and not isinstance(
            variant,
            str,
        ):
            raise TypeError(
                "variant must be str or None"
            )

        if rollout_basis_points is not None:
            if (
                not isinstance(
                    rollout_basis_points,
                    int,
                )
                or rollout_basis_points < 0
                or rollout_basis_points > 10000
            ):
                raise ValueError(
                    "rollout_basis_points must be int 0..10000"
                )

            if not isinstance(
                rollout_variant,
                str,
            ) or rollout_variant == "":
                raise ValueError(
                    "rollout_variant required when rollout is configured"
                )

        elif rollout_variant is not None:
            raise ValueError(
                "rollout_variant requires rollout_basis_points"
            )

        if (
            variant is not None
            and rollout_basis_points is not None
        ):
            raise ValueError(
                "rule cannot use both fixed variant and rollout"
            )

        if (
            variant is None
            and rollout_basis_points is None
        ):
            raise ValueError(
                "rule requires variant or rollout"
            )

        if not isinstance(
            salt,
            str,
        ):
            raise TypeError(
                "salt must be str"
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

        self.rule_id = rule_id
        self.conditions = (
            normalized_conditions
        )
        self.variant = variant
        self.rollout_basis_points = (
            rollout_basis_points
        )
        self.rollout_variant = (
            rollout_variant
        )
        self.salt = salt
        self.enabled = bool(
            enabled
        )
        self.metadata = self._copy(
            metadata
        )

    def to_dict(
        self,
    ):
        return {
            "rule_id": self.rule_id,
            "conditions": self._copy(
                self.conditions
            ),
            "variant": self.variant,
            "rollout_basis_points": (
                self.rollout_basis_points
            ),
            "rollout_variant": (
                self.rollout_variant
            ),
            "salt": self.salt,
            "enabled": self.enabled,
            "metadata": self._copy(
                self.metadata
            ),
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
