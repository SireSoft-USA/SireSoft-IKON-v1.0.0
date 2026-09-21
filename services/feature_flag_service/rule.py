class TargetingRule:
    """
    Ordered feature-flag targeting rule.

    Supported operators:
      eq, neq, in, not_in, prefix, contains

    A rule may either select a fixed variant or apply a deterministic rollout
    percentage (basis points 0..10000) to one variant.
    """

    OPERATORS = (
        "eq",
        "neq",
        "in",
        "not_in",
        "prefix",
        "contains",
    )

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
        if not isinstance(rule_id, str) or rule_id == "":
            raise ValueError(
                "rule_id must be non-empty str"
            )

        if conditions is None:
            conditions = []

        if not isinstance(conditions, list):
            raise TypeError(
                "conditions must be list or None"
            )

        normalized_conditions = []

        for condition in conditions:
            if not isinstance(condition, dict):
                raise TypeError(
                    "each condition must be dict"
                )

            attribute = condition.get(
                "attribute"
            )
            operator = condition.get(
                "operator"
            )

            if not isinstance(attribute, str) or attribute == "":
                raise ValueError(
                    "condition attribute must be non-empty str"
                )

            if operator not in self.OPERATORS:
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

        if variant is not None and rollout_basis_points is not None:
            raise ValueError(
                "rule cannot use both fixed variant and rollout"
            )

        if variant is None and rollout_basis_points is None:
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

        if not isinstance(metadata, dict):
            raise TypeError(
                "metadata must be dict or None"
            )

        self.rule_id = rule_id
        self.conditions = normalized_conditions
        self.variant = variant
        self.rollout_basis_points = rollout_basis_points
        self.rollout_variant = rollout_variant
        self.salt = salt
        self.enabled = bool(
            enabled
        )
        self.metadata = self._copy(
            metadata
        )

    def matches(
        self,
        attributes,
    ):
        if not self.enabled:
            return False

        if attributes is None:
            attributes = {}

        if not isinstance(
            attributes,
            dict,
        ):
            raise TypeError(
                "attributes must be dict or None"
            )

        for condition in self.conditions:
            attribute = condition[
                "attribute"
            ]

            if attribute not in attributes:
                return False

            actual = attributes[
                attribute
            ]
            expected = condition[
                "value"
            ]
            operator = condition[
                "operator"
            ]

            if not self._condition_matches(
                actual,
                operator,
                expected,
            ):
                return False

        return True

    def public_dict(
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
                "targeting rule state must be dict"
            )

        return cls(
            rule_id=value[
                "rule_id"
            ],
            conditions=value.get(
                "conditions",
                [],
            ),
            variant=value.get(
                "variant"
            ),
            rollout_basis_points=value.get(
                "rollout_basis_points"
            ),
            rollout_variant=value.get(
                "rollout_variant"
            ),
            salt=value.get(
                "salt",
                "",
            ),
            enabled=value.get(
                "enabled",
                True,
            ),
            metadata=value.get(
                "metadata",
                {},
            ),
        )

    def _condition_matches(
        self,
        actual,
        operator,
        expected,
    ):
        if operator == "eq":
            return actual == expected

        if operator == "neq":
            return actual != expected

        if operator == "in":
            if not isinstance(
                expected,
                (list, tuple),
            ):
                raise TypeError(
                    "in operator expects list/tuple condition value"
                )

            return actual in expected

        if operator == "not_in":
            if not isinstance(
                expected,
                (list, tuple),
            ):
                raise TypeError(
                    "not_in operator expects list/tuple condition value"
                )

            return actual not in expected

        if operator == "prefix":
            return (
                isinstance(
                    actual,
                    str,
                )
                and isinstance(
                    expected,
                    str,
                )
                and actual.startswith(
                    expected
                )
            )

        if operator == "contains":
            if isinstance(
                actual,
                str,
            ) and isinstance(
                expected,
                str,
            ):
                return expected in actual

            if isinstance(
                actual,
                (list, tuple),
            ):
                return expected in actual

            return False

        return False

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
