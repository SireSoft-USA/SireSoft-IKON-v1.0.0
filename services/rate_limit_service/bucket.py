class TokenBucket:
    """
    Integer token bucket with deterministic refill accounting.

    Time is supplied explicitly as integer seconds. Refills happen in complete
    refill periods, carrying the unused remainder forward.
    """

    def __init__(
        self,
        policy,
        now,
    ):
        if not isinstance(
            policy,
            RateLimitPolicy,
        ):
            raise TypeError(
                "policy must be RateLimitPolicy"
            )

        self._validate_now(
            now
        )

        self.policy_id = (
            policy.policy_id
        )

        self.tokens = (
            policy.capacity
        )

        self.last_refill = int(
            now
        )

        self.total_allowed = 0
        self.total_denied = 0
        self.total_charged = 0

    def inspect(
        self,
        policy,
        now,
        cost=None,
    ):
        self._ensure_policy(
            policy
        )

        self._refill(
            policy,
            now,
        )

        effective_cost = (
            policy.cost
            if cost is None
            else cost
        )

        self._validate_cost(
            policy,
            effective_cost,
        )

        allowed = (
            not policy.enabled
            or self.tokens
            >= effective_cost
        )

        retry_after = 0

        if (
            policy.enabled
            and not allowed
        ):
            retry_after = (
                self._retry_after(
                    policy,
                    effective_cost,
                    now,
                )
            )

        return {
            "allowed": allowed,
            "policy_id": (
                policy.policy_id
            ),
            "cost": effective_cost,
            "remaining_tokens": (
                self.tokens
            ),
            "capacity": (
                policy.capacity
            ),
            "retry_after_seconds": (
                retry_after
            ),
            "enabled": (
                policy.enabled
            ),
        }

    def consume(
        self,
        policy,
        now,
        cost=None,
    ):
        result = self.inspect(
            policy,
            now,
            cost=cost,
        )

        if not policy.enabled:
            self.total_allowed += 1
            return result

        if result[
            "allowed"
        ]:
            charged = result[
                "cost"
            ]

            self.tokens -= charged
            self.total_allowed += 1
            self.total_charged += (
                charged
            )

            result[
                "remaining_tokens"
            ] = self.tokens

        else:
            self.total_denied += 1

        return result

    def reset(
        self,
        policy,
        now,
    ):
        self._ensure_policy(
            policy
        )

        self._validate_now(
            now
        )

        self.tokens = (
            policy.capacity
        )

        self.last_refill = int(
            now
        )

        self.total_allowed = 0
        self.total_denied = 0
        self.total_charged = 0

        return self.state()

    def state(
        self,
    ):
        return {
            "policy_id": (
                self.policy_id
            ),
            "tokens": self.tokens,
            "last_refill": (
                self.last_refill
            ),
            "total_allowed": (
                self.total_allowed
            ),
            "total_denied": (
                self.total_denied
            ),
            "total_charged": (
                self.total_charged
            ),
        }

    def _refill(
        self,
        policy,
        now,
    ):
        self._validate_now(
            now
        )

        now = int(
            now
        )

        if now < self.last_refill:
            raise ValueError(
                "rate-limit time cannot move backwards"
            )

        elapsed = (
            now
            - self.last_refill
        )

        periods = (
            elapsed
            // policy.refill_seconds
        )

        if periods <= 0:
            return

        refill = (
            periods
            * policy.refill_tokens
        )

        self.tokens = min(
            policy.capacity,
            self.tokens
            + refill,
        )

        self.last_refill += (
            periods
            * policy.refill_seconds
        )

    def _retry_after(
        self,
        policy,
        cost,
        now,
    ):
        missing = (
            cost
            - self.tokens
        )

        if missing <= 0:
            return 0

        periods = (
            missing
            + policy.refill_tokens
            - 1
        ) // policy.refill_tokens

        target = (
            self.last_refill
            + (
                periods
                * policy.refill_seconds
            )
        )

        wait = (
            target
            - int(
                now
            )
        )

        if wait < 0:
            return 0

        return wait

    def _ensure_policy(
        self,
        policy,
    ):
        if not isinstance(
            policy,
            RateLimitPolicy,
        ):
            raise TypeError(
                "policy must be RateLimitPolicy"
            )

        if (
            policy.policy_id
            != self.policy_id
        ):
            raise ValueError(
                "bucket policy identity mismatch"
            )

    def _validate_cost(
        self,
        policy,
        cost,
    ):
        if (
            not isinstance(
                cost,
                int,
            )
            or cost <= 0
        ):
            raise ValueError(
                "cost must be positive int"
            )

        if cost > policy.capacity:
            raise ValueError(
                "cost cannot exceed policy capacity"
            )

    def _validate_now(
        self,
        now,
    ):
        if not isinstance(
            now,
            int,
        ):
            raise TypeError(
                "now must be integer seconds"
            )

        if now < 0:
            raise ValueError(
                "now must be non-negative"
            )
