class LogSanitizer:
    """
    Conservative structured-log redaction.

    It redacts known sensitive field names recursively and masks simple inline
    credential assignments in messages. This is a guardrail, not a complete
    secret-detection system.
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

    INLINE_MARKERS = (
        "password=",
        "passwd=",
        "token=",
        "access_token=",
        "refresh_token=",
        "api_key=",
        "apikey=",
        "secret=",
        "authorization:",
        "bearer ",
    )

    REDACTED = "[REDACTED]"

    def sanitize_message(
        self,
        text,
    ):
        if not isinstance(
            text,
            str,
        ):
            raise TypeError(
                "log message must be str"
            )

        result = text

        for marker in self.INLINE_MARKERS:
            result = self._mask_marker(
                result,
                marker,
            )

        return result

    def sanitize_fields(
        self,
        fields,
    ):
        if fields is None:
            return {}

        if not isinstance(
            fields,
            dict,
        ):
            raise TypeError(
                "log fields must be dict or None"
            )

        return self._sanitize_value(
            fields,
            key_name=None,
        )

    def _sanitize_value(
        self,
        value,
        key_name,
    ):
        if (
            key_name is not None
            and self._sensitive_key(
                key_name
            )
        ):
            return self.REDACTED

        if isinstance(
            value,
            dict,
        ):
            result = {}

            for key in value:
                result[
                    key
                ] = self._sanitize_value(
                    value[
                        key
                    ],
                    str(
                        key
                    ),
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

        if isinstance(
            value,
            str,
        ):
            return self.sanitize_message(
                value
            )

        return value

    def _sensitive_key(
        self,
        key,
    ):
        normalized = str(
            key
        ).strip().lower()

        return normalized in self.SENSITIVE_KEYS

    def _mask_marker(
        self,
        text,
        marker,
    ):
        lower = text.lower()
        marker_lower = marker.lower()
        start = 0

        while True:
            index = lower.find(
                marker_lower,
                start,
            )

            if index < 0:
                break

            value_start = (
                index
                + len(
                    marker
                )
            )

            value_end = (
                value_start
            )

            while (
                value_end
                < len(
                    text
                )
            ):
                char = text[
                    value_end
                ]

                if char in (
                    " ",
                    "\t",
                    "\r",
                    "\n",
                    ",",
                    ";",
                    ")",
                    "]",
                    "}",
                ):
                    break

                value_end += 1

            if value_end == value_start:
                start = value_start
                continue

            text = (
                text[
                    :value_start
                ]
                + self.REDACTED
                + text[
                    value_end:
                ]
            )

            lower = text.lower()

            start = (
                value_start
                + len(
                    self.REDACTED
                )
            )

        return text
