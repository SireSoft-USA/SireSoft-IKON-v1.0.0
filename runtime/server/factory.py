class RuntimeServerFactory:
    """
    Creates the complete local runtime and binds it to HTTP without starting it.
    """

    def __init__(
        self,
        composition_builder=None,
    ):
        self.composition_builder = (
            RuntimeCompositionBuilder()
            if composition_builder
            is None
            else composition_builder
        )

    def create(
        self,
        system_spec,
        server_config,
    ):
        if not isinstance(
            system_spec,
            RuntimeSystemSpec,
        ):
            raise TypeError(
                "system_spec must be RuntimeSystemSpec"
            )

        if not isinstance(
            server_config,
            RuntimeServerConfig,
        ):
            raise TypeError(
                "server_config must be RuntimeServerConfig"
            )

        system = (
            self.composition_builder
            .build(
                system_spec
            )
        )

        return RuntimeHTTPApplicationServer(
            system=system,
            config=server_config,
        )
