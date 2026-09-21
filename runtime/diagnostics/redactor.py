class DiagnosticRedactor:
    DEFAULT_SENSITIVE_KEYS = (
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
        "private_key",
    )

    def __init__(
        self,
        replacement="[REDACTED]",
        sensitive_keys=None,
    ):
        if not isinstance(replacement, str) or replacement == "":
            raise ValueError("replacement must be non-empty str")

        if sensitive_keys is None:
            sensitive_keys = self.DEFAULT_SENSITIVE_KEYS

        if not isinstance(sensitive_keys, (list, tuple)):
            raise TypeError(
                "sensitive_keys must be list/tuple or None"
            )

        self.replacement = replacement
        self._keys = {}

        for key in sensitive_keys:
            if not isinstance(key, str) or key == "":
                raise ValueError(
                    "sensitive keys must be non-empty strings"
                )

            self._keys[key.lower()] = True

    def redact(
        self,
        value,
    ):
        return self._redact(
            value,
            None,
        )

    def _redact(
        self,
        value,
        parent_key,
    ):
        if (
            parent_key is not None
            and parent_key.lower() in self._keys
        ):
            return self.replacement

        if isinstance(value, dict):
            result = {}

            for key in value:
                string_key = str(key)
                result[string_key] = self._redact(
                    value[key],
                    string_key,
                )

            return result

        if isinstance(value, (list, tuple)):
            return [
                self._redact(
                    item,
                    parent_key,
                )
                for item in value
            ]

        return value
