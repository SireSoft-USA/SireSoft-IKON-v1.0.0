class FeatureFlagsConfigFactory:
    def build_manager(
        self,
        config,
        event_bus=None,
        persistence=None,
    ):
        if not isinstance(
            config,
            FeatureFlagsConfig,
        ):
            raise TypeError(
                "config must be FeatureFlagsConfig"
            )

        FeatureFlagsConfigValidator().require_valid(
            config
        )

        if (
            config.publish_events
            and event_bus is None
        ):
            raise ValueError(
                "event_bus is required when publish_events=True"
            )

        manager = FeatureFlagManager(
            persistence=(
                persistence
            ),
            event_bus=(
                event_bus
                if config.publish_events
                else None
            ),
        )

        for flag in config.flags:
            manager.create_flag(
                flag_key=(
                    flag.flag_key
                ),
                variants=(
                    flag.variants
                ),
                default_variant=(
                    flag.default_variant
                ),
                disabled_variant=(
                    flag.disabled_variant
                ),
                enabled=flag.enabled,
                description=(
                    flag.description
                ),
                metadata=(
                    flag.metadata
                ),
            )

            for rule in flag.rules:
                manager.add_rule(
                    flag_key=(
                        flag.flag_key
                    ),
                    rule_id=(
                        rule.rule_id
                    ),
                    conditions=(
                        rule.conditions
                    ),
                    variant=(
                        rule.variant
                    ),
                    rollout_basis_points=(
                        rule.rollout_basis_points
                    ),
                    rollout_variant=(
                        rule.rollout_variant
                    ),
                    salt=rule.salt,
                    enabled=(
                        rule.enabled
                    ),
                    metadata=(
                        rule.metadata
                    ),
                )

        return manager

    def initialize(
        self,
        config,
        event_bus=None,
        persistence=None,
        load_persisted=False,
    ):
        manager = self.build_manager(
            config,
            event_bus=event_bus,
            persistence=persistence,
        )

        if (
            load_persisted
            and config.persistence_path
            is not None
        ):
            manager.load_state_file(
                config.persistence_path
            )

        return manager
