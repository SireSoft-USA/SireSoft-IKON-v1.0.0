class RuntimeGatewayFactory:
    """
    Builds an APIGateway whose dispatcher is the composed RuntimeSystem.
    """

    def build(
        self,
        system,
        config,
    ):
        if not isinstance(
            system,
            RuntimeSystem,
        ):
            raise TypeError(
                "system must be RuntimeSystem"
            )

        if not isinstance(
            config,
            RuntimeServerConfig,
        ):
            raise TypeError(
                "config must be RuntimeServerConfig"
            )

        router = GatewayRouter()

        for route in config.routes:
            router.add(
                route
            )

        return APIGateway(
            router=router,
            middleware=(
                config.middleware
            ),
            dispatcher=(
                system.dispatch
            ),
        )
