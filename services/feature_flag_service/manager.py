class FeatureFlagManager:
    """
    Runtime feature-flag registry with ordered rules, deterministic rollout,
    persistence, and optional EventBus change notifications.
    """

    def __init__(
        self,
        evaluator=None,
        persistence=None,
        event_bus=None,
    ):
        self.evaluator = (
            FeatureFlagEvaluator()
            if evaluator is None
            else evaluator
        )

        self.persistence = (
            FeatureFlagPersistence()
            if persistence is None
            else persistence
        )

        self.event_bus = event_bus

        self._flags = {}
        self._order = []
        self.version = 0
        self.total_evaluations = 0

    def create_flag(
        self,
        flag_key,
        variants,
        default_variant,
        disabled_variant,
        enabled=True,
        description="",
        metadata=None,
        timestamp=None,
    ):
        if flag_key in self._flags:
            raise ValueError(
                "feature flag already exists: "
                + str(
                    flag_key
                )
            )

        flag = FeatureFlag(
            flag_key=flag_key,
            variants=variants,
            default_variant=default_variant,
            disabled_variant=disabled_variant,
            enabled=enabled,
            description=description,
            metadata=metadata,
        )

        self._flags[
            flag_key
        ] = flag

        self._order.append(
            flag_key
        )

        self.version += 1

        self._publish_change(
            "feature_flag.created",
            flag,
            timestamp,
        )

        return flag

    def delete_flag(
        self,
        flag_key,
        timestamp=None,
    ):
        flag = self.get_flag(
            flag_key
        )

        del self._flags[
            flag_key
        ]

        self._order = [
            existing
            for existing in self._order
            if existing != flag_key
        ]

        self.version += 1

        self._publish_change(
            "feature_flag.deleted",
            flag,
            timestamp,
        )

        return flag

    def get_flag(
        self,
        flag_key,
    ):
        if flag_key not in self._flags:
            raise KeyError(
                "feature flag not found: "
                + str(
                    flag_key
                )
            )

        return self._flags[
            flag_key
        ]

    def list_flags(
        self,
    ):
        return [
            self._flags[
                flag_key
            ].public_dict()
            for flag_key
            in self._order
        ]

    def set_enabled(
        self,
        flag_key,
        enabled,
        timestamp=None,
    ):
        flag = self.get_flag(
            flag_key
        )

        flag.set_enabled(
            enabled
        )

        self.version += 1

        self._publish_change(
            "feature_flag.updated",
            flag,
            timestamp,
        )

        return flag

    def add_rule(
        self,
        flag_key,
        rule_id,
        conditions=None,
        variant=None,
        rollout_basis_points=None,
        rollout_variant=None,
        salt="",
        enabled=True,
        metadata=None,
        timestamp=None,
    ):
        flag = self.get_flag(
            flag_key
        )

        rule = TargetingRule(
            rule_id=rule_id,
            conditions=conditions,
            variant=variant,
            rollout_basis_points=(
                rollout_basis_points
            ),
            rollout_variant=(
                rollout_variant
            ),
            salt=salt,
            enabled=enabled,
            metadata=metadata,
        )

        flag.add_rule(
            rule
        )

        self.version += 1

        self._publish_change(
            "feature_flag.updated",
            flag,
            timestamp,
        )

        return rule

    def remove_rule(
        self,
        flag_key,
        rule_id,
        timestamp=None,
    ):
        flag = self.get_flag(
            flag_key
        )

        rule = flag.remove_rule(
            rule_id
        )

        self.version += 1

        self._publish_change(
            "feature_flag.updated",
            flag,
            timestamp,
        )

        return rule

    def evaluate(
        self,
        flag_key,
        subject_key,
        attributes=None,
    ):
        flag = self.get_flag(
            flag_key
        )

        result = self.evaluator.evaluate(
            flag=flag,
            subject_key=subject_key,
            attributes=attributes,
        )

        self.total_evaluations += 1

        result[
            "manager_version"
        ] = self.version

        return result

    def save_state(
        self,
        path,
    ):
        return self.persistence.save(
            path,
            self,
        )

    def load_state_file(
        self,
        path,
    ):
        return self.persistence.load(
            path,
            self,
        )

    def export_state(
        self,
    ):
        return {
            "format": (
                "SireLLMFeatureFlagState"
            ),
            "version": 1,
            "manager_version": (
                self.version
            ),
            "total_evaluations": (
                self.total_evaluations
            ),
            "flags": [
                self._flags[
                    flag_key
                ].public_dict()
                for flag_key
                in self._order
            ],
        }

    def load_state(
        self,
        state,
    ):
        if not isinstance(
            state,
            dict,
        ):
            raise TypeError(
                "feature-flag manager state must be dict"
            )

        if state.get(
            "format"
        ) != "SireLLMFeatureFlagState":
            raise ValueError(
                "invalid feature-flag state format"
            )

        if int(
            state.get(
                "version",
                0,
            )
        ) != 1:
            raise ValueError(
                "unsupported feature-flag state version"
            )

        staged = {}
        order = []

        for flag_state in state.get(
            "flags",
            [],
        ):
            flag = FeatureFlag.from_dict(
                flag_state
            )

            if flag.flag_key in staged:
                raise ValueError(
                    "duplicate feature flag in state"
                )

            staged[
                flag.flag_key
            ] = flag

            order.append(
                flag.flag_key
            )

        self._flags = staged
        self._order = order
        self.version = int(
            state.get(
                "manager_version",
                0,
            )
        )
        self.total_evaluations = int(
            state.get(
                "total_evaluations",
                0,
            )
        )

        return self

    def status(
        self,
    ):
        enabled = 0
        disabled = 0
        rules = 0

        for flag_key in self._order:
            flag = self._flags[
                flag_key
            ]

            if flag.enabled:
                enabled += 1
            else:
                disabled += 1

            rules += len(
                flag.rules()
            )

        return {
            "ready": True,
            "flag_count": len(
                self._order
            ),
            "enabled_flags": enabled,
            "disabled_flags": disabled,
            "rule_count": rules,
            "manager_version": (
                self.version
            ),
            "total_evaluations": (
                self.total_evaluations
            ),
            "event_bus_attached": (
                self.event_bus
                is not None
            ),
        }

    def _publish_change(
        self,
        topic,
        flag,
        timestamp,
    ):
        if self.event_bus is None:
            return

        if timestamp is None:
            return

        if not isinstance(
            timestamp,
            int,
        ) or timestamp < 0:
            raise ValueError(
                "timestamp must be non-negative int"
            )

        if not hasattr(
            self.event_bus,
            "publish",
        ):
            raise TypeError(
                "event_bus must provide publish()"
            )

        self.event_bus.publish(
            topic=topic,
            timestamp=timestamp,
            payload={
                "flag_key": (
                    flag.flag_key
                ),
                "enabled": (
                    flag.enabled
                ),
                "manager_version": (
                    self.version
                ),
            },
            source_service=(
                "feature_flag_service"
            ),
        )
