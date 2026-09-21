class SecretsConfig:
    """
    Secret definitions only. Raw secret values are deliberately excluded.
    """

    def __init__(
        self,
        secrets,
        attach_events=False,
        attach_audit=False,
        metadata=None,
    ):
        if not isinstance(
            secrets,
            (list, tuple),
        ) or len(
            secrets
        ) == 0:
            raise ValueError(
                "secrets must be non-empty list/tuple"
            )

        normalized = []
        seen = {}

        for secret in secrets:
            if not isinstance(
                secret,
                SecretDefinitionConfig,
            ):
                raise TypeError(
                    "secrets entries must be SecretDefinitionConfig"
                )

            if secret.secret_id in seen:
                raise ValueError(
                    "duplicate secret_id: "
                    + secret.secret_id
                )

            seen[
                secret.secret_id
            ] = True

            normalized.append(
                secret
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

        self.secrets = normalized
        self.attach_events = bool(
            attach_events
        )
        self.attach_audit = bool(
            attach_audit
        )
        self.metadata = self._copy(
            metadata
        )

    def secret_map(
        self,
    ):
        return {
            secret.secret_id: secret
            for secret
            in self.secrets
        }

    def to_dict(
        self,
    ):
        return {
            "secrets": [
                secret.to_dict()
                for secret
                in self.secrets
            ],
            "attach_events": (
                self.attach_events
            ),
            "attach_audit": (
                self.attach_audit
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
