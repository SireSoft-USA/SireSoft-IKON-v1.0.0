class AuthConfigFactory:
    """
    Builds runtime auth components while keeping server_secret out of config.
    """

    def build_permission_policy(
        self,
        config,
    ):
        if not isinstance(
            config,
            AuthConfig,
        ):
            raise TypeError(
                "config must be AuthConfig"
            )

        return PermissionPolicy(
            roles=(
                config.role_map()
            )
        )

    def build_manager(
        self,
        config,
        server_secret,
    ):
        if not isinstance(
            config,
            AuthConfig,
        ):
            raise TypeError(
                "config must be AuthConfig"
            )

        return AuthManager(
            server_secret=(
                server_secret
            ),
            password_iterations=(
                config
                .password_iterations
            ),
            min_password_length=(
                config
                .min_password_length
            ),
            max_failed_attempts=(
                config
                .max_failed_attempts
            ),
            permission_policy=(
                self.build_permission_policy(
                    config
                )
            ),
        )

    def build_gateway_middleware(
        self,
        config,
        auth_manager,
        now_provider,
    ):
        if not isinstance(
            config,
            AuthConfig,
        ):
            raise TypeError(
                "config must be AuthConfig"
            )

        return (
            GatewayTokenAuthenticationMiddleware(
                auth_manager=(
                    auth_manager
                ),
                now_provider=(
                    now_provider
                ),
                permission_by_route=(
                    config
                    .permission_by_route
                ),
            )
        )
