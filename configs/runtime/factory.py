class RuntimeProfileFactory:
    """
    Converts a typed RuntimeProfile into the runtime config objects already
    implemented by the composition/server/daemon layers.
    """

    def build_system_spec(
        self,
        profile,
        time_provider,
        service_bindings=None,
        process_specs=None,
    ):
        if not isinstance(
            profile,
            RuntimeProfile,
        ):
            raise TypeError(
                "profile must be RuntimeProfile"
            )

        if not callable(
            time_provider
        ):
            raise TypeError(
                "time_provider must be callable"
            )

        if service_bindings is None:
            service_bindings = []

        if process_specs is None:
            process_specs = []

        return RuntimeSystemSpec(
            storage_root=(
                profile.storage_root
            ),
            time_provider=(
                time_provider
            ),
            worker_count=(
                profile.worker_count
            ),
            queue_capacity=(
                profile.queue_capacity
            ),
            storage_namespaces=(
                profile.storage_namespaces
            ),
            process_specs=list(
                process_specs
            ),
            service_bindings=list(
                service_bindings
            ),
            enable_signals=(
                profile.enable_signals
            ),
            metadata={
                "runtime_profile": (
                    profile.name
                ),
                "profile_metadata": (
                    dict(
                        profile.metadata
                    )
                ),
            },
        )

    def build_server_config(
        self,
        profile,
        routes=None,
        middleware=None,
        context_enricher=None,
    ):
        if not isinstance(
            profile,
            RuntimeProfile,
        ):
            raise TypeError(
                "profile must be RuntimeProfile"
            )

        return RuntimeServerConfig(
            host=profile.host,
            port=profile.port,
            routes=(
                []
                if routes is None
                else list(
                    routes
                )
            ),
            middleware=middleware,
            context_enricher=(
                context_enricher
            ),
            backlog=profile.backlog,
            timeout_seconds=(
                profile.timeout_seconds
            ),
            recv_chunk_bytes=(
                profile.recv_chunk_bytes
            ),
        )

    def build_daemon_config(
        self,
        profile,
    ):
        if not isinstance(
            profile,
            RuntimeProfile,
        ):
            raise TypeError(
                "profile must be RuntimeProfile"
            )

        return RuntimeDaemonConfig(
            max_requests=(
                profile.max_requests
            ),
            max_idle_timeouts=(
                profile.max_idle_timeouts
            ),
        )
