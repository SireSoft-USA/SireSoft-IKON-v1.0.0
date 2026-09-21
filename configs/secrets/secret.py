class SecretDefinitionConfig:
    """
    Defines a secret identity, ACL and metadata without containing its value.

    Actual secret material must be supplied at runtime by a value_provider.
    """

    FORBIDDEN_METADATA_KEYS = (
        "value",
        "secret",
        "secret_value",
        "password",
        "token",
        "api_key",
        "private_key",
    )

    def __init__(
        self,
        secret_id,
        policy=None,
        enabled=True,
        purpose=None,
        metadata=None,
    ):
        if not isinstance(
            secret_id,
            str,
        ) or secret_id == "":
            raise ValueError(
                "secret_id must be non-empty str"
            )

        if policy is None:
            policy = (
                SecretPolicyConfig()
            )

        if not isinstance(
            policy,
            SecretPolicyConfig,
        ):
            raise TypeError(
                "policy must be SecretPolicyConfig or None"
            )

        if purpose is not None and (
            not isinstance(
                purpose,
                str,
            )
            or purpose == ""
        ):
            raise ValueError(
                "purpose must be non-empty str or None"
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

        self._reject_secret_material(
            metadata
        )

        self.secret_id = secret_id
        self.policy = policy
        self.enabled = bool(
            enabled
        )
        self.purpose = purpose
        self.metadata = self._copy(
            metadata
        )

    def to_dict(
        self,
    ):
        return {
            "secret_id": (
                self.secret_id
            ),
            "policy": (
                self.policy.to_dict()
            ),
            "enabled": (
                self.enabled
            ),
            "purpose": (
                self.purpose
            ),
            "metadata": self._copy(
                self.metadata
            ),
        }

    def _reject_secret_material(
        self,
        value,
    ):
        for key in value:
            normalized = str(
                key
            ).lower()

            if normalized in self.FORBIDDEN_METADATA_KEYS:
                raise ValueError(
                    "secret material is not allowed in config metadata: "
                    + str(
                        key
                    )
                )

            nested = value[
                key
            ]

            if isinstance(
                nested,
                dict,
            ):
                self._reject_secret_material(
                    nested
                )

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
