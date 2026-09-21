class FeatureFlagsConfigCodec:
    def __init__(
        self,
        parser=None,
    ):
        self.parser = (
            JSONParser()
            if parser is None
            else parser
        )

    def decode_text(
        self,
        text,
    ):
        if not isinstance(
            text,
            str,
        ):
            raise TypeError(
                "feature-flags config text must be str"
            )

        return self.from_dict(
            self.parser.parse(
                text
            )
        )

    def from_dict(
        self,
        value,
    ):
        if not isinstance(
            value,
            dict,
        ):
            raise ValueError(
                "feature-flags config root must be object"
            )

        raw_flags = value.get(
            "flags"
        )

        if not isinstance(
            raw_flags,
            list,
        ) or len(
            raw_flags
        ) == 0:
            raise ValueError(
                "flags must be non-empty list"
            )

        flags = []

        for raw_flag in raw_flags:
            if not isinstance(
                raw_flag,
                dict,
            ):
                raise ValueError(
                    "feature flag entry must be object"
                )

            raw_rules = raw_flag.get(
                "rules",
                [],
            )

            if not isinstance(
                raw_rules,
                list,
            ):
                raise ValueError(
                    "feature flag rules must be list"
                )

            rules = []

            for raw_rule in raw_rules:
                if not isinstance(
                    raw_rule,
                    dict,
                ):
                    raise ValueError(
                        "feature flag rule entry must be object"
                    )

                rules.append(
                    FeatureFlagRuleConfig(
                        rule_id=raw_rule.get(
                            "rule_id"
                        ),
                        conditions=raw_rule.get(
                            "conditions",
                            [],
                        ),
                        variant=raw_rule.get(
                            "variant"
                        ),
                        rollout_basis_points=(
                            raw_rule.get(
                                "rollout_basis_points"
                            )
                        ),
                        rollout_variant=(
                            raw_rule.get(
                                "rollout_variant"
                            )
                        ),
                        salt=raw_rule.get(
                            "salt",
                            "",
                        ),
                        enabled=raw_rule.get(
                            "enabled",
                            True,
                        ),
                        metadata=raw_rule.get(
                            "metadata",
                            {},
                        ),
                    )
                )

            flags.append(
                FeatureFlagConfig(
                    flag_key=raw_flag.get(
                        "flag_key"
                    ),
                    variants=raw_flag.get(
                        "variants"
                    ),
                    default_variant=(
                        raw_flag.get(
                            "default_variant"
                        )
                    ),
                    disabled_variant=(
                        raw_flag.get(
                            "disabled_variant"
                        )
                    ),
                    rules=rules,
                    enabled=raw_flag.get(
                        "enabled",
                        True,
                    ),
                    description=raw_flag.get(
                        "description",
                        "",
                    ),
                    metadata=raw_flag.get(
                        "metadata",
                        {},
                    ),
                )
            )

        return FeatureFlagsConfig(
            flags=flags,
            persistence_path=value.get(
                "persistence_path"
            ),
            publish_events=value.get(
                "publish_events",
                False,
            ),
            metadata=value.get(
                "metadata",
                {},
            ),
        )
