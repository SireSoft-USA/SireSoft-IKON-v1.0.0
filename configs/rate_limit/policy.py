class RateLimitPolicyConfig:
    """
    Serializable token-bucket policy configuration.
    """

    def __init__(
        self,
        policy_id,
        capacity,
        refill_tokens,
        refill_seconds,
        cost=1,
        enabled=True,
        metadata=None,
    ):
        if not isinstance(
            policy_id,
            str,
        ) or policy_id == "":
            raise ValueError(
                "policy_id must be non-empty str"
            )

        for name, value in (
            (
                "capacity",
                capacity,
            ),
            (
                "refill_tokens",
                refill_tokens,
            ),
            (
                "refill_seconds",
                refill_seconds,
            ),
            (
                "cost",
                cost,
            ),
        ):
            if (
                not isinstance(
                    value,
                    int,
                )
                or value <= 0
            ):
                raise ValueError(
                    name
                    + " must be positive int"
                )

        if cost > capacity:
            raise ValueError(
                "cost cannot exceed capacity"
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

        self.policy_id = policy_id
        self.capacity = capacity
        self.refill_tokens = (
            refill_tokens
        )
        self.refill_seconds = (
            refill_seconds
        )
        self.cost = cost
        self.enabled = bool(
            enabled
        )
        self.metadata = self._copy(
            metadata
        )

    def to_dict(
        self,
    ):
        return {
            "policy_id": (
                self.policy_id
            ),
            "capacity": self.capacity,
            "refill_tokens": (
                self.refill_tokens
            ),
            "refill_seconds": (
                self.refill_seconds
            ),
            "cost": self.cost,
            "enabled": self.enabled,
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
