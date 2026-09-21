class RateLimitConfigCodec:
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
                "rate-limit config text must be str"
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
                "rate-limit config root must be object"
            )

        raw_policies = value.get(
            "policies"
        )

        if not isinstance(
            raw_policies,
            list,
        ) or len(
            raw_policies
        ) == 0:
            raise ValueError(
                "policies must be non-empty list"
            )

        policies = []

        for raw in raw_policies:
            if not isinstance(
                raw,
                dict,
            ):
                raise ValueError(
                    "rate-limit policy entry must be object"
                )

            policies.append(
                RateLimitPolicyConfig(
                    policy_id=raw.get(
                        "policy_id"
                    ),
                    capacity=raw.get(
                        "capacity"
                    ),
                    refill_tokens=raw.get(
                        "refill_tokens"
                    ),
                    refill_seconds=raw.get(
                        "refill_seconds"
                    ),
                    cost=raw.get(
                        "cost",
                        1,
                    ),
                    enabled=raw.get(
                        "enabled",
                        True,
                    ),
                    metadata=raw.get(
                        "metadata",
                        {},
                    ),
                )
            )

        return RateLimitConfig(
            policies=policies,
            policy_by_route=value.get(
                "policy_by_route",
                {},
            ),
            default_policy_id=value.get(
                "default_policy_id"
            ),
            client_id_header=value.get(
                "client_id_header",
                "x-client-id",
            ),
            metadata=value.get(
                "metadata",
                {},
            ),
        )
