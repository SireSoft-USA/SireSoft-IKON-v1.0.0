class RateLimitManager:
    """
    Owns policies and per-key token buckets.

    Bucket identity is scoped by policy + logical key:
      policy_id|key

    Keys can represent users, API clients, sessions, tenants, or anonymous
    traffic labels resolved by the gateway adapter.
    """

    def __init__(
        self,
    ):
        self._policies = {}
        self._policy_order = []

        self._buckets = {}
        self._bucket_order = []

        self.total_checks = 0
        self.total_consumes = 0
        self.total_allowed = 0
        self.total_denied = 0

    def configure_policy(
        self,
        policy_id,
        capacity,
        refill_tokens,
        refill_seconds,
        cost=1,
        enabled=True,
        metadata=None,
        replace=False,
    ):
        exists = (
            policy_id
            in self._policies
        )

        if (
            exists
            and not replace
        ):
            raise ValueError(
                "rate-limit policy already exists: "
                + str(
                    policy_id
                )
            )

        policy = RateLimitPolicy(
            policy_id=policy_id,
            capacity=capacity,
            refill_tokens=(
                refill_tokens
            ),
            refill_seconds=(
                refill_seconds
            ),
            cost=cost,
            enabled=enabled,
            metadata=metadata,
        )

        self._policies[
            policy_id
        ] = policy

        if not exists:
            self._policy_order.append(
                policy_id
            )

        if exists:
            self._reset_policy_buckets(
                policy_id
            )

        return policy

    def remove_policy(
        self,
        policy_id,
    ):
        policy = self.get_policy(
            policy_id
        )

        del self._policies[
            policy_id
        ]

        self._policy_order = [
            existing
            for existing
            in self._policy_order
            if existing
            != policy_id
        ]

        self._reset_policy_buckets(
            policy_id
        )

        return policy

    def get_policy(
        self,
        policy_id,
    ):
        if policy_id not in self._policies:
            raise KeyError(
                "rate-limit policy not found: "
                + str(
                    policy_id
                )
            )

        return self._policies[
            policy_id
        ]

    def list_policies(
        self,
    ):
        return [
            self._policies[
                policy_id
            ].to_dict()
            for policy_id
            in self._policy_order
        ]

    def check(
        self,
        policy_id,
        key,
        now,
        cost=None,
    ):
        self._validate_key(
            key
        )

        policy = self.get_policy(
            policy_id
        )

        bucket = self._bucket(
            policy,
            key,
            now,
        )

        self.total_checks += 1

        result = bucket.inspect(
            policy,
            now,
            cost=cost,
        )

        return self._decorate(
            result,
            key,
            consumed=False,
        )

    def consume(
        self,
        policy_id,
        key,
        now,
        cost=None,
    ):
        self._validate_key(
            key
        )

        policy = self.get_policy(
            policy_id
        )

        bucket = self._bucket(
            policy,
            key,
            now,
        )

        self.total_consumes += 1

        result = bucket.consume(
            policy,
            now,
            cost=cost,
        )

        if result[
            "allowed"
        ]:
            self.total_allowed += 1

        else:
            self.total_denied += 1

        return self._decorate(
            result,
            key,
            consumed=True,
        )

    def reset_key(
        self,
        policy_id,
        key,
        now,
    ):
        self._validate_key(
            key
        )

        policy = self.get_policy(
            policy_id
        )

        bucket = self._bucket(
            policy,
            key,
            now,
        )

        state = bucket.reset(
            policy,
            now,
        )

        return {
            "policy_id": (
                policy_id
            ),
            "key": key,
            "bucket": state,
        }

    def reset_all(
        self,
    ):
        count = len(
            self._bucket_order
        )

        self._buckets = {}
        self._bucket_order = []

        self.total_checks = 0
        self.total_consumes = 0
        self.total_allowed = 0
        self.total_denied = 0

        return {
            "cleared_buckets": count,
        }

    def bucket_state(
        self,
        policy_id,
        key,
    ):
        self._validate_key(
            key
        )

        self.get_policy(
            policy_id
        )

        bucket_id = self._bucket_id(
            policy_id,
            key,
        )

        if bucket_id not in self._buckets:
            return None

        return {
            "policy_id": (
                policy_id
            ),
            "key": key,
            "bucket": (
                self._buckets[
                    bucket_id
                ].state()
            ),
        }

    def status(
        self,
    ):
        policy_states = []

        for policy_id in self._policy_order:
            policy_states.append(
                self._policies[
                    policy_id
                ].to_dict()
            )

        return {
            "ready": True,
            "policies": policy_states,
            "policy_count": len(
                policy_states
            ),
            "bucket_count": len(
                self._bucket_order
            ),
            "total_checks": (
                self.total_checks
            ),
            "total_consumes": (
                self.total_consumes
            ),
            "total_allowed": (
                self.total_allowed
            ),
            "total_denied": (
                self.total_denied
            ),
            "algorithm": (
                "integer_token_bucket"
            ),
        }

    def _bucket(
        self,
        policy,
        key,
        now,
    ):
        bucket_id = self._bucket_id(
            policy.policy_id,
            key,
        )

        if bucket_id not in self._buckets:
            self._buckets[
                bucket_id
            ] = TokenBucket(
                policy,
                now,
            )

            self._bucket_order.append(
                bucket_id
            )

        return self._buckets[
            bucket_id
        ]

    def _bucket_id(
        self,
        policy_id,
        key,
    ):
        return (
            policy_id
            + "|"
            + key
        )

    def _decorate(
        self,
        result,
        key,
        consumed,
    ):
        output = dict(
            result
        )

        output[
            "key"
        ] = key

        output[
            "consumed"
        ] = bool(
            consumed
        )

        return output

    def _reset_policy_buckets(
        self,
        policy_id,
    ):
        remaining = []

        for bucket_id in self._bucket_order:
            prefix = (
                policy_id
                + "|"
            )

            if bucket_id.startswith(
                prefix
            ):
                if bucket_id in self._buckets:
                    del self._buckets[
                        bucket_id
                    ]
            else:
                remaining.append(
                    bucket_id
                )

        self._bucket_order = (
            remaining
        )

    def _validate_key(
        self,
        key,
    ):
        if not isinstance(
            key,
            str,
        ) or key == "":
            raise ValueError(
                "rate-limit key must be non-empty str"
            )
