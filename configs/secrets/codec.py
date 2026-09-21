class SecretsConfigCodec:
    """
    Handwritten-JSON backed config decoder.

    A top-level or per-secret "value" field is explicitly rejected so config
    files cannot silently become secret stores.
    """

    def __init__(
        self,
        parser=None,
    ):
        self.parser = (
            JSONParser()
            if parser is None
            else parser
        )

    def decode_text(
        self,
        text,
    ):
        if not isinstance(
            text,
            str,
        ):
            raise TypeError(
                "secrets config text must be str"
            )

        return self.from_dict(
            self.parser.parse(
                text
            )
        )

    def from_dict(
        self,
        value,
    ):
        if not isinstance(
            value,
            dict,
        ):
            raise ValueError(
                "secrets config root must be object"
            )

        if (
            "value" in value
            or "secret_value" in value
        ):
            raise ValueError(
                "raw secret material is forbidden in secrets config"
            )

        raw_secrets = value.get(
            "secrets"
        )

        if not isinstance(
            raw_secrets,
            list,
        ) or len(
            raw_secrets
        ) == 0:
            raise ValueError(
                "secrets must be non-empty list"
            )

        secrets = []

        for raw in raw_secrets:
            if not isinstance(
                raw,
                dict,
            ):
                raise ValueError(
                    "secret definition must be object"
                )

            if (
                "value" in raw
                or "secret_value" in raw
            ):
                raise ValueError(
                    "raw secret material is forbidden in secret definitions"
                )

            raw_policy = raw.get(
                "policy",
                {},
            )

            if not isinstance(
                raw_policy,
                dict,
            ):
                raise ValueError(
                    "secret policy must be object"
                )

            policy = SecretPolicyConfig(
                readers=raw_policy.get(
                    "readers"
                ),
                writers=raw_policy.get(
                    "writers"
                ),
                admins=raw_policy.get(
                    "admins"
                ),
            )

            secrets.append(
                SecretDefinitionConfig(
                    secret_id=raw.get(
                        "secret_id"
                    ),
                    policy=policy,
                    enabled=raw.get(
                        "enabled",
                        True,
                    ),
                    purpose=raw.get(
                        "purpose"
                    ),
                    metadata=raw.get(
                        "metadata",
                        {},
                    ),
                )
            )

        return SecretsConfig(
            secrets=secrets,
            attach_events=value.get(
                "attach_events",
                False,
            ),
            attach_audit=value.get(
                "attach_audit",
                False,
            ),
            metadata=value.get(
                "metadata",
                {},
            ),
        )
