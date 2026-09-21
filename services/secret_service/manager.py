class SecretManager:
    """
    In-memory secret manager with explicit ACLs, version rotation, audit hooks,
    and redacted public views.

    Raw secret values are never returned by service/public methods. Internal
    runtime components use resolve_secret() directly.
    """

    def __init__(
        self,
        sanitizer=None,
        event_bus=None,
        audit_manager=None,
    ):
        self.sanitizer = (
            SecretMetadataSanitizer()
            if sanitizer is None
            else sanitizer
        )

        self.event_bus = event_bus
        self.audit_manager = (
            audit_manager
        )

        self._secrets = {}
        self._order = []

        self.total_reads = 0
        self.total_denied_reads = 0
        self.total_rotations = 0
        self.total_destroyed = 0

    def create_secret(
        self,
        secret_id,
        value,
        actor_id,
        now,
        readers=None,
        writers=None,
        admins=None,
        metadata=None,
        trace_id=None,
        correlation_id=None,
    ):
        self._validate_actor_time(
            actor_id,
            now,
        )

        if secret_id in self._secrets:
            raise ValueError(
                "secret already exists: "
                + str(
                    secret_id
                )
            )

        normalized_admins = (
            []
            if admins is None
            else list(
                admins
            )
        )

        if actor_id not in normalized_admins:
            normalized_admins.append(
                actor_id
            )

        policy = SecretAccessPolicy(
            readers=readers,
            writers=writers,
            admins=normalized_admins,
        )

        record = SecretRecord(
            secret_id=secret_id,
            value=value,
            created_at=now,
            created_by=actor_id,
            policy=policy,
            metadata=(
                self.sanitizer
                .sanitize(
                    metadata
                )
            ),
        )

        self._secrets[
            secret_id
        ] = record

        self._order.append(
            secret_id
        )

        self._emit(
            "secret.created",
            record,
            actor_id,
            now,
            "success",
            trace_id,
            correlation_id,
        )

        return record

    def rotate_secret(
        self,
        secret_id,
        value,
        actor_id,
        now,
        metadata=None,
        trace_id=None,
        correlation_id=None,
    ):
        self._validate_actor_time(
            actor_id,
            now,
        )

        record = self.get_secret(
            secret_id
        )

        if not record.policy.can_write(
            actor_id
        ):
            self._emit(
                "secret.rotation_denied",
                record,
                actor_id,
                now,
                "denied",
                trace_id,
                correlation_id,
            )

            raise PermissionError(
                "principal cannot rotate secret"
            )

        version = record.rotate(
            value=value,
            created_at=now,
            created_by=actor_id,
            metadata=(
                self.sanitizer
                .sanitize(
                    metadata
                )
            ),
        )

        self.total_rotations += 1

        self._emit(
            "secret.rotated",
            record,
            actor_id,
            now,
            "success",
            trace_id,
            correlation_id,
        )

        return version

    def resolve_secret(
        self,
        secret_id,
        actor_id,
        now,
        version=None,
        purpose=None,
        trace_id=None,
        correlation_id=None,
    ):
        self._validate_actor_time(
            actor_id,
            now,
        )

        record = self.get_secret(
            secret_id
        )

        if not record.policy.can_read(
            actor_id
        ):
            self.total_denied_reads += 1

            self._emit(
                "secret.access_denied",
                record,
                actor_id,
                now,
                "denied",
                trace_id,
                correlation_id,
                metadata={
                    "purpose": purpose,
                },
            )

            raise PermissionError(
                "principal cannot read secret"
            )

        value = record.resolve(
            version=version
        )

        self.total_reads += 1

        self._emit(
            "secret.accessed",
            record,
            actor_id,
            now,
            "success",
            trace_id,
            correlation_id,
            metadata={
                "purpose": purpose,
                "version": (
                    record.public_dict()[
                        "current_version"
                    ]
                    if version is None
                    else version
                ),
            },
        )

        return value

    def check_access(
        self,
        secret_id,
        actor_id,
        action,
    ):
        record = self.get_secret(
            secret_id
        )

        if action == "read":
            allowed = record.policy.can_read(
                actor_id
            )

        elif action == "write":
            allowed = record.policy.can_write(
                actor_id
            )

        elif action == "admin":
            allowed = record.policy.can_admin(
                actor_id
            )

        else:
            raise ValueError(
                "action must be read, write, or admin"
            )

        return {
            "secret_id": (
                secret_id
            ),
            "actor_id": (
                actor_id
            ),
            "action": action,
            "allowed": (
                allowed
                and record.enabled
                and not record.destroyed
            ),
        }

    def set_policy(
        self,
        secret_id,
        actor_id,
        now,
        readers=None,
        writers=None,
        admins=None,
        trace_id=None,
        correlation_id=None,
    ):
        self._validate_actor_time(
            actor_id,
            now,
        )

        record = self.get_secret(
            secret_id
        )

        if not record.policy.can_admin(
            actor_id
        ):
            self._emit(
                "secret.policy_denied",
                record,
                actor_id,
                now,
                "denied",
                trace_id,
                correlation_id,
            )

            raise PermissionError(
                "principal cannot change secret policy"
            )

        record.policy.replace(
            readers=readers,
            writers=writers,
            admins=admins,
        )

        if not record.policy.can_admin(
            actor_id
        ):
            raise ValueError(
                "policy update cannot remove the acting admin"
            )

        self._emit(
            "secret.policy_updated",
            record,
            actor_id,
            now,
            "success",
            trace_id,
            correlation_id,
        )

        return record

    def disable_secret(
        self,
        secret_id,
        actor_id,
        now,
        trace_id=None,
        correlation_id=None,
    ):
        record = self._require_admin(
            secret_id,
            actor_id,
            now,
        )

        record.disable()

        self._emit(
            "secret.disabled",
            record,
            actor_id,
            now,
            "success",
            trace_id,
            correlation_id,
        )

        return record

    def enable_secret(
        self,
        secret_id,
        actor_id,
        now,
        trace_id=None,
        correlation_id=None,
    ):
        record = self._require_admin(
            secret_id,
            actor_id,
            now,
        )

        record.enable()

        self._emit(
            "secret.enabled",
            record,
            actor_id,
            now,
            "success",
            trace_id,
            correlation_id,
        )

        return record

    def destroy_secret(
        self,
        secret_id,
        actor_id,
        now,
        trace_id=None,
        correlation_id=None,
    ):
        record = self._require_admin(
            secret_id,
            actor_id,
            now,
        )

        record.destroy()

        self.total_destroyed += 1

        self._emit(
            "secret.destroyed",
            record,
            actor_id,
            now,
            "success",
            trace_id,
            correlation_id,
        )

        return record

    def get_secret(
        self,
        secret_id,
    ):
        if secret_id not in self._secrets:
            raise KeyError(
                "secret not found: "
                + str(
                    secret_id
                )
            )

        return self._secrets[
            secret_id
        ]

    def public_get(
        self,
        secret_id,
    ):
        return self.get_secret(
            secret_id
        ).public_dict()

    def list_secrets(
        self,
    ):
        return [
            self._secrets[
                secret_id
            ].public_dict()
            for secret_id
            in self._order
        ]

    def status(
        self,
    ):
        enabled = 0
        disabled = 0
        destroyed = 0
        versions = 0

        for secret_id in self._order:
            record = self._secrets[
                secret_id
            ]

            versions += record.public_dict()[
                "version_count"
            ]

            if record.destroyed:
                destroyed += 1
            elif record.enabled:
                enabled += 1
            else:
                disabled += 1

        return {
            "ready": True,
            "storage_mode": (
                "in_memory_only"
            ),
            "secret_count": len(
                self._order
            ),
            "enabled_secrets": (
                enabled
            ),
            "disabled_secrets": (
                disabled
            ),
            "destroyed_secrets": (
                destroyed
            ),
            "version_count": (
                versions
            ),
            "total_reads": (
                self.total_reads
            ),
            "total_denied_reads": (
                self.total_denied_reads
            ),
            "total_rotations": (
                self.total_rotations
            ),
            "total_destroyed": (
                self.total_destroyed
            ),
            "event_bus_attached": (
                self.event_bus
                is not None
            ),
            "audit_attached": (
                self.audit_manager
                is not None
            ),
        }

    def _require_admin(
        self,
        secret_id,
        actor_id,
        now,
    ):
        self._validate_actor_time(
            actor_id,
            now,
        )

        record = self.get_secret(
            secret_id
        )

        if not record.policy.can_admin(
            actor_id
        ):
            raise PermissionError(
                "principal cannot administer secret"
            )

        return record

    def _validate_actor_time(
        self,
        actor_id,
        now,
    ):
        if not isinstance(
            actor_id,
            str,
        ) or actor_id == "":
            raise ValueError(
                "actor_id must be non-empty str"
            )

        if (
            not isinstance(
                now,
                int,
            )
            or now < 0
        ):
            raise ValueError(
                "now must be non-negative int"
            )

    def _emit(
        self,
        topic,
        record,
        actor_id,
        now,
        outcome,
        trace_id,
        correlation_id,
        metadata=None,
    ):
        if metadata is None:
            metadata = {}

        safe_metadata = (
            self.sanitizer
            .sanitize(
                metadata
            )
        )

        if self.event_bus is not None:
            self.event_bus.publish(
                topic=topic,
                timestamp=now,
                payload={
                    "secret_id": (
                        record.secret_id
                    ),
                    "actor_id": (
                        actor_id
                    ),
                    "outcome": (
                        outcome
                    ),
                    "current_version": (
                        record.public_dict()[
                            "current_version"
                        ]
                    ),
                    "metadata": (
                        safe_metadata
                    ),
                },
                source_service=(
                    "secret_service"
                ),
                trace_id=trace_id,
                correlation_id=(
                    correlation_id
                ),
            )

        if self.audit_manager is not None:
            self.audit_manager.record(
                timestamp=now,
                actor_id=actor_id,
                actor_type="principal",
                action=topic,
                resource=(
                    "secret:"
                    + record.secret_id
                ),
                outcome=outcome,
                metadata={
                    "current_version": (
                        record.public_dict()[
                            "current_version"
                        ]
                    ),
                    "details": (
                        safe_metadata
                    ),
                },
                trace_id=trace_id,
                correlation_id=(
                    correlation_id
                ),
            )
