class AuditPolicyConfig:
    """
    Describes runtime expectations for the append-only audit service.

    The underlying implementation always sanitizes common secret-bearing
    metadata keys and uses an FNV-1a linked hash chain. Those implementation
    facts are exposed here as explicit policy expectations rather than toggles,
    preventing configuration from silently disabling them.
    """

    INTEGRITY_SCHEMES = (
        "fnv1a64_hash_chain",
    )

    def __init__(
        self,
        require_metadata_sanitization=True,
        expected_integrity_scheme=(
            "fnv1a64_hash_chain"
        ),
        require_append_only=True,
    ):
        if expected_integrity_scheme not in (
            self.INTEGRITY_SCHEMES
        ):
            raise ValueError(
                "unsupported expected_integrity_scheme"
            )

        self.require_metadata_sanitization = bool(
            require_metadata_sanitization
        )
        self.expected_integrity_scheme = (
            expected_integrity_scheme
        )
        self.require_append_only = bool(
            require_append_only
        )

    def to_dict(
        self,
    ):
        return {
            "require_metadata_sanitization": (
                self.require_metadata_sanitization
            ),
            "expected_integrity_scheme": (
                self.expected_integrity_scheme
            ),
            "require_append_only": (
                self.require_append_only
            ),
        }
