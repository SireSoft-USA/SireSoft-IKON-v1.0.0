class FeatureFlagEvaluator:
    """
    Ordered rule evaluator with deterministic percentage rollout.
    """

    def evaluate(
        self,
        flag,
        subject_key,
        attributes=None,
    ):
        if not isinstance(
            flag,
            FeatureFlag,
        ):
            raise TypeError(
                "flag must be FeatureFlag"
            )

        if not isinstance(
            subject_key,
            str,
        ) or subject_key == "":
            raise ValueError(
                "subject_key must be non-empty str"
            )

        if attributes is None:
            attributes = {}

        if not isinstance(
            attributes,
            dict,
        ):
            raise TypeError(
                "attributes must be dict or None"
            )

        if not flag.enabled:
            return self._result(
                flag=flag,
                variant=(
                    flag.disabled_variant
                ),
                reason="flag_disabled",
                rule_id=None,
                rollout_bucket=None,
            )

        for rule in flag.rules():
            if not rule.matches(
                attributes
            ):
                continue

            if rule.variant is not None:
                return self._result(
                    flag=flag,
                    variant=(
                        rule.variant
                    ),
                    reason="rule_match",
                    rule_id=(
                        rule.rule_id
                    ),
                    rollout_bucket=None,
                )

            bucket = self._bucket(
                flag.flag_key,
                subject_key,
                rule.salt,
            )

            if (
                bucket
                < rule.rollout_basis_points
            ):
                return self._result(
                    flag=flag,
                    variant=(
                        rule.rollout_variant
                    ),
                    reason=(
                        "rollout_match"
                    ),
                    rule_id=(
                        rule.rule_id
                    ),
                    rollout_bucket=(
                        bucket
                    ),
                )

            # A matching rollout rule that does not include this subject falls
            # through to later rules/default.

        return self._result(
            flag=flag,
            variant=(
                flag.default_variant
            ),
            reason="default",
            rule_id=None,
            rollout_bucket=None,
        )

    def _bucket(
        self,
        flag_key,
        subject_key,
        salt,
    ):
        raw = (
            flag_key
            + "|"
            + subject_key
            + "|"
            + salt
        )

        return (
            fnv1a64(
                raw.encode(
                    "utf-8"
                )
            )
            % 10000
        )

    def _result(
        self,
        flag,
        variant,
        reason,
        rule_id,
        rollout_bucket,
    ):
        return {
            "flag_key": (
                flag.flag_key
            ),
            "variant": variant,
            "value": flag._copy(
                flag.variants[
                    variant
                ]
            ),
            "reason": reason,
            "rule_id": rule_id,
            "rollout_bucket": (
                rollout_bucket
            ),
        }
