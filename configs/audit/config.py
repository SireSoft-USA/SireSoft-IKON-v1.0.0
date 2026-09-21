class AuditConfig:
    def __init__(
        self,
        policy=None,
        persistence=None,
        attach_event_bus=False,
        metadata=None,
    ):
        if policy is None:
            policy = (
                AuditPolicyConfig()
            )

        if persistence is None:
            persistence = (
                AuditPersistenceConfig()
            )

        if not isinstance(
            policy,
            AuditPolicyConfig,
        ):
            raise TypeError(
                "policy must be AuditPolicyConfig"
            )

        if not isinstance(
            persistence,
            AuditPersistenceConfig,
        ):
            raise TypeError(
                "persistence must be AuditPersistenceConfig"
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

        self.policy = policy
        self.persistence = persistence
        self.attach_event_bus = bool(
            attach_event_bus
        )
        self.metadata = self._copy(
            metadata
        )

    def to_dict(
        self,
    ):
        return {
            "policy": (
                self.policy.to_dict()
            ),
            "persistence": (
                self.persistence
                .to_dict()
            ),
            "attach_event_bus": (
                self.attach_event_bus
            ),
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
