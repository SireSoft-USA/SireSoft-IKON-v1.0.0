class RateLimitConfig:
    """
    Complete API-gateway rate-limit configuration.
    """

    def __init__(
        self,
        policies,
        policy_by_route=None,
        default_policy_id=None,
        client_id_header="x-client-id",
        metadata=None,
    ):
        if not isinstance(
            policies,
            (list, tuple),
        ) or len(
            policies
        ) == 0:
            raise ValueError(
                "policies must be non-empty list/tuple"
            )

        normalized = []
        seen = {}

        for policy in policies:
            if not isinstance(
                policy,
                RateLimitPolicyConfig,
            ):
                raise TypeError(
                    "policies entries must be RateLimitPolicyConfig"
                )

            if policy.policy_id in seen:
                raise ValueError(
                    "duplicate rate-limit policy: "
                    + policy.policy_id
                )

            seen[
                policy.policy_id
            ] = True
            normalized.append(
                policy
            )

        if policy_by_route is None:
            policy_by_route = {}

        if not isinstance(
            policy_by_route,
            dict,
        ):
            raise TypeError(
                "policy_by_route must be dict or None"
            )

        normalized_routes = {}

        for route_key in policy_by_route:
            policy_id = (
                policy_by_route[
                    route_key
                ]
            )

            if (
                not isinstance(
                    route_key,
                    str,
                )
                or route_key == ""
            ):
                raise ValueError(
                    "route keys must be non-empty strings"
                )

            if (
                not isinstance(
                    policy_id,
                    str,
                )
                or policy_id == ""
            ):
                raise ValueError(
                    "route policy ids must be non-empty strings"
                )

            normalized_routes[
                route_key
            ] = policy_id

        if default_policy_id is not None and (
            not isinstance(
                default_policy_id,
                str,
            )
            or default_policy_id == ""
        ):
            raise ValueError(
                "default_policy_id must be non-empty str or None"
            )

        if not isinstance(
            client_id_header,
            str,
        ) or client_id_header.strip() == "":
            raise ValueError(
                "client_id_header must be non-empty str"
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

        self.policies = normalized
        self.policy_by_route = (
            normalized_routes
        )
        self.default_policy_id = (
            default_policy_id
        )
        self.client_id_header = (
            client_id_header
            .strip()
            .lower()
        )
        self.metadata = self._copy(
            metadata
        )

    def policy_map(
        self,
    ):
        return {
            policy.policy_id: policy
            for policy
            in self.policies
        }

    def to_dict(
        self,
    ):
        return {
            "policies": [
                policy.to_dict()
                for policy
                in self.policies
            ],
            "policy_by_route": dict(
                self.policy_by_route
            ),
            "default_policy_id": (
                self.default_policy_id
            ),
            "client_id_header": (
                self.client_id_header
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
