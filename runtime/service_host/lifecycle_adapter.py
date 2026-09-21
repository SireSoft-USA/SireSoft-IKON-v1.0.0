class ServiceHostLifecycleAdapter:
    """
    Lifecycle adapter for runtime/lifecycle.
    """

    @staticmethod
    def resource(
        name,
        host,
        now_provider,
        dependencies=None,
        metadata=None,
    ):
        if not isinstance(
            host,
            ServiceHost,
        ):
            raise TypeError(
                "host must be ServiceHost"
            )

        if not callable(
            now_provider
        ):
            raise TypeError(
                "now_provider must be callable"
            )

        def start_host():
            now = now_provider()

            return host.start(
                now
            )

        return LifecycleResource(
            name=name,
            start_callback=(
                start_host
            ),
            stop_callback=(
                host.stop
            ),
            dependencies=dependencies,
            metadata=metadata,
        )
