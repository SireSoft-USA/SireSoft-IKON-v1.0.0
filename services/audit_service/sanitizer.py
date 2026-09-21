class AuditSanitizer:
    """
    Redacts common secrets from structured audit metadata.

    Audit records should describe security-relevant actions without storing
    authentication secrets, passwords, raw tokens, or API keys.
    """

    SENSITIVE_KEYS = (
        "password",
        "passwd",
        "token",
        "access_token",
        "refresh_token",
        "authorization",
        "cookie",
        "set-cookie",
        "api_key",
        "apikey",
        "secret",
        "credential",
        "credentials",
    )

    REDACTED = "[REDACTED]"

    def sanitize(self, metadata):
        if metadata is None:
            return {}

        if not isinstance(metadata, dict):
            raise TypeError("audit metadata must be dict or None")

        return self._sanitize_value(
            metadata,
            None,
        )

    def _sanitize_value(self, value, key_name):
        if (
            key_name is not None
            and self._sensitive_key(key_name)
        ):
            return self.REDACTED

        if isinstance(value, dict):
            result = {}
            for key in value:
                result[key] = self._sanitize_value(
                    value[key],
                    str(key),
                )
            return result

        if isinstance(value, list):
            return [
                self._sanitize_value(item, None)
                for item in value
            ]

        if isinstance(value, tuple):
            return [
                self._sanitize_value(item, None)
                for item in value
            ]

        return value

    def _sensitive_key(self, key):
        return (
            str(key).strip().lower()
            in self.SENSITIVE_KEYS
        )
