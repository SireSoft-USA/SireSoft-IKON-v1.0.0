class RuntimeSignalLifecycleAdapter:
    @staticmethod
    def resource(
        name,
        signal_handler,
        dependencies=None,
        metadata=None,
    ):
        if not isinstance(
            signal_handler,
            RuntimeSignalHandler,
        ):
            raise TypeError(
                "signal_handler must be RuntimeSignalHandler"
            )

        return LifecycleResource(
            name=name,
            start_callback=(
                signal_handler.install
            ),
            stop_callback=(
                signal_handler.restore
            ),
            dependencies=dependencies,
            metadata=metadata,
        )
