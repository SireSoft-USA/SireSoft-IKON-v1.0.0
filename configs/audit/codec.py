class AuditConfigCodec:
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
                "audit config text must be str"
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
                "audit config root must be object"
            )

        policy = value.get(
            "policy",
            {},
        )

        persistence = value.get(
            "persistence",
            {},
        )

        if not isinstance(
            policy,
            dict,
        ):
            raise ValueError(
                "policy section must be object"
            )

        if not isinstance(
            persistence,
            dict,
        ):
            raise ValueError(
                "persistence section must be object"
            )

        return AuditConfig(
            policy=(
                AuditPolicyConfig(
                    require_metadata_sanitization=(
                        policy.get(
                            "require_metadata_sanitization",
                            True,
                        )
                    ),
                    expected_integrity_scheme=(
                        policy.get(
                            "expected_integrity_scheme",
                            (
                                "fnv1a64_hash_chain"
                            ),
                        )
                    ),
                    require_append_only=(
                        policy.get(
                            "require_append_only",
                            True,
                        )
                    ),
                )
            ),
            persistence=(
                AuditPersistenceConfig(
                    state_path=(
                        persistence.get(
                            "state_path"
                        )
                    ),
                    load_state_on_start=(
                        persistence.get(
                            "load_state_on_start",
                            False,
                        )
                    ),
                )
            ),
            attach_event_bus=(
                value.get(
                    "attach_event_bus",
                    False,
                )
            ),
            metadata=value.get(
                "metadata",
                {},
            ),
        )
