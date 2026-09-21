class AuditConfigFactory:
    """
    Builds the real append-only AuditManager/AuditService.

    EventBus and file-system paths are runtime wiring. Secret sanitization and
    hash-chain integrity remain properties of the actual audit implementation.
    """

    def build_manager(
        self,
        config,
        event_bus=None,
        persistence=None,
    ):
        if not isinstance(
            config,
            AuditConfig,
        ):
            raise TypeError(
                "config must be AuditConfig"
            )

        AuditConfigValidator().require_valid(
            config
        )

        if (
            config.attach_event_bus
            and event_bus is None
        ):
            raise ValueError(
                "audit config requires event_bus"
            )

        manager = AuditManager(
            persistence=persistence,
            event_bus=(
                event_bus
                if config
                .attach_event_bus
                else None
            ),
        )

        if (
            config
            .persistence
            .load_state_on_start
        ):
            manager.load_state_file(
                config
                .persistence
                .state_path
            )

        self._verify_runtime_policy(
            manager,
            config,
        )

        return manager

    def build_service(
        self,
        config,
        event_bus=None,
        persistence=None,
    ):
        return AuditService(
            self.build_manager(
                config,
                event_bus=event_bus,
                persistence=persistence,
            )
        )

    def save_state(
        self,
        manager,
        config,
        path_override=None,
    ):
        if not isinstance(
            manager,
            AuditManager,
        ):
            raise TypeError(
                "manager must be AuditManager"
            )

        if not isinstance(
            config,
            AuditConfig,
        ):
            raise TypeError(
                "config must be AuditConfig"
            )

        path = (
            config
            .persistence
            .state_path
            if path_override is None
            else path_override
        )

        if path is None:
            raise ValueError(
                "audit state path is not configured"
            )

        return manager.save_state(
            path
        )

    def _verify_runtime_policy(
        self,
        manager,
        config,
    ):
        status = manager.status()

        if (
            status[
                "integrity_scheme"
            ]
            != config
            .policy
            .expected_integrity_scheme
        ):
            raise ValueError(
                "audit runtime integrity scheme does not match configuration"
            )

        if (
            config.policy
            .require_metadata_sanitization
            and not isinstance(
                manager.sanitizer,
                AuditSanitizer,
            )
        ):
            raise TypeError(
                "configured audit policy requires AuditSanitizer"
            )

        return True
