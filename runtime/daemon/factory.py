class RuntimeDaemonFactory:
    def __init__(
        self,
        server_factory=None,
    ):
        self.server_factory = (
            RuntimeServerFactory()
            if server_factory is None
            else server_factory
        )

    def create(
        self,
        system_spec,
        server_config,
        daemon_config=None,
    ):
        server = (
            self.server_factory
            .create(
                system_spec,
                server_config,
            )
        )

        loop = RuntimeServeLoop(
            server=server,
            config=(
                RuntimeDaemonConfig()
                if daemon_config
                is None
                else daemon_config
            ),
        )

        return RuntimeDaemon(
            server=server,
            loop=loop,
        )
