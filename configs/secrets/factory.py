class SecretsConfigFactory:
    """
    Creates SecretManager and injects secret values only at runtime.

    value_provider(secret_id) is the only path by which raw secret material
    enters the manager from this config layer.
    """

    def build_manager(
        self,
        config,
        sanitizer=None,
        event_bus=None,
        audit_manager=None,
    ):
        if not isinstance(
            config,
            SecretsConfig,
        ):
            raise TypeError(
                "config must be SecretsConfig"
            )

        SecretsConfigValidator().require_valid(
            config
        )

        if (
            config.attach_events
            and event_bus is None
        ):
            raise ValueError(
                "event_bus is required when attach_events=True"
            )

        if (
            config.attach_audit
            and audit_manager is None
        ):
            raise ValueError(
                "audit_manager is required when attach_audit=True"
            )

        return SecretManager(
            sanitizer=sanitizer,
            event_bus=(
                event_bus
                if config.attach_events
                else None
            ),
            audit_manager=(
                audit_manager
                if config.attach_audit
                else None
            ),
        )

    def initialize(
        self,
        config,
        value_provider,
        actor_id,
        now_provider,
        manager=None,
        sanitizer=None,
        event_bus=None,
        audit_manager=None,
    ):
        if not isinstance(
            config,
            SecretsConfig,
        ):
            raise TypeError(
                "config must be SecretsConfig"
            )

        if not callable(
            value_provider
        ):
            raise TypeError(
                "value_provider must be callable"
            )

        if not isinstance(
            actor_id,
            str,
        ) or actor_id == "":
            raise ValueError(
                "actor_id must be non-empty str"
            )

        if not callable(
            now_provider
        ):
            raise TypeError(
                "now_provider must be callable"
            )

        if manager is None:
            manager = self.build_manager(
                config,
                sanitizer=sanitizer,
                event_bus=event_bus,
                audit_manager=(
                    audit_manager
                ),
            )

        if not isinstance(
            manager,
            SecretManager,
        ):
            raise TypeError(
                "manager must be SecretManager or None"
            )

        initialized = []

        for secret in config.secrets:
            value = value_provider(
                secret.secret_id
            )

            if not isinstance(
                value,
                str,
            ) or value == "":
                raise ValueError(
                    "value_provider must return non-empty str for "
                    + secret.secret_id
                )

            now = now_provider()

            record = manager.create_secret(
                secret_id=(
                    secret.secret_id
                ),
                value=value,
                actor_id=actor_id,
                now=now,
                readers=(
                    secret.policy.readers
                ),
                writers=(
                    secret.policy.writers
                ),
                admins=(
                    secret.policy.admins
                ),
                metadata={
                    "purpose": (
                        secret.purpose
                    ),
                    "config_metadata": (
                        secret.metadata
                    ),
                },
            )

            if not secret.enabled:
                manager.disable_secret(
                    secret_id=(
                        secret.secret_id
                    ),
                    actor_id=(
                        actor_id
                    ),
                    now=now_provider(),
                )

            initialized.append(
                record.public_dict()
            )

        return {
            "manager": manager,
            "initialized": initialized,
            "count": len(
                initialized
            ),
        }
