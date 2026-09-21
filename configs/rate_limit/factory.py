class RateLimitConfigFactory:
    """
    Builds runtime rate-limit manager/middleware from serializable config.
    """

    def build_manager(
        self,
        config,
    ):
        if not isinstance(
            config,
            RateLimitConfig,
        ):
            raise TypeError(
                "config must be RateLimitConfig"
            )

        manager = (
            RateLimitManager()
        )

        for policy in config.policies:
            manager.configure_policy(
                policy_id=(
                    policy.policy_id
                ),
                capacity=(
                    policy.capacity
                ),
                refill_tokens=(
                    policy.refill_tokens
                ),
                refill_seconds=(
                    policy.refill_seconds
                ),
                cost=(
                    policy.cost
                ),
                enabled=(
                    policy.enabled
                ),
                metadata=(
                    policy.metadata
                ),
            )

        return manager

    def build_gateway_middleware(
        self,
        config,
        manager,
        now_provider,
    ):
        if not isinstance(
            config,
            RateLimitConfig,
        ):
            raise TypeError(
                "config must be RateLimitConfig"
            )

        if not isinstance(
            manager,
            RateLimitManager,
        ):
            raise TypeError(
                "manager must be RateLimitManager"
            )

        if not callable(
            now_provider
        ):
            raise TypeError(
                "now_provider must be callable"
            )

        return GatewayRateLimitMiddleware(
            rate_limit_manager=(
                manager
            ),
            now_provider=(
                now_provider
            ),
            policy_by_route=(
                config
                .policy_by_route
            ),
            default_policy_id=(
                config
                .default_policy_id
            ),
            client_id_header=(
                config
                .client_id_header
            ),
        )
