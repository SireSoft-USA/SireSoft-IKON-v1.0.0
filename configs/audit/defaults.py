def default_audit_config():
    return AuditConfig(
        policy=(
            AuditPolicyConfig(
                require_metadata_sanitization=True,
                expected_integrity_scheme=(
                    "fnv1a64_hash_chain"
                ),
                require_append_only=True,
            )
        ),
        persistence=(
            AuditPersistenceConfig(
                state_path=(
                    "runtime/state/"
                    "audit.sllmaud"
                ),
                load_state_on_start=False,
            )
        ),
        attach_event_bus=True,
        metadata={
            "profile": "sirellm",
            "record_model": (
                "append-only"
            ),
        },
    )
