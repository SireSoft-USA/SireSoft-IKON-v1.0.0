class SecretMetadataSanitizer:
    """
    Prevents obvious secret-bearing metadata fields from becoming a secondary
    accidental storage location for raw credentials.
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
        "value",
    )

    REDACTED = "[REDACTED]"

    def sanitize(
        self,
        metadata,
    ):
        if metadata is None:
            return {}

        if not isinstance(
            metadata,
            dict,
        ):
            raise TypeError(
                "secret metadata must be dict or None"
            )

        return self._sanitize_value(
            metadata,
            None,
        )

    def _sanitize_value(
        self,
        value,
        key,
    ):
        if (
            key is not None
            and str(
                key
            ).strip().lower()
            in self.SENSITIVE_KEYS
        ):
            return self.REDACTED

        if isinstance(
            value,
            dict,
        ):
            result = {}

            for child_key in value:
                result[
                    child_key
                ] = self._sanitize_value(
                    value[
                        child_key
                    ],
                    child_key,
                )

            return result

        if isinstance(
            value,
            list,
        ):
            return [
                self._sanitize_value(
                    item,
                    None,
                )
                for item in value
            ]

        if isinstance(
            value,
            tuple,
        ):
            return [
                self._sanitize_value(
                    item,
                    None,
                )
                for item in value
            ]

        return value
