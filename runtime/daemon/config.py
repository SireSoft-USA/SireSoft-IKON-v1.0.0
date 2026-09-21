class RuntimeDaemonConfig:
    """
    Long-running server-loop configuration.

    max_requests/max_idle_timeouts exist mainly for deterministic execution and
    testing. None means no explicit limit.
    """

    def __init__(
        self,
        max_requests=None,
        max_idle_timeouts=None,
        stop_on_server_error=True,
    ):
        if max_requests is not None and (
            not isinstance(
                max_requests,
                int,
            )
            or max_requests <= 0
        ):
            raise ValueError(
                "max_requests must be positive int or None"
            )

        if max_idle_timeouts is not None and (
            not isinstance(
                max_idle_timeouts,
                int,
            )
            or max_idle_timeouts <= 0
        ):
            raise ValueError(
                "max_idle_timeouts must be positive int or None"
            )

        self.max_requests = max_requests
        self.max_idle_timeouts = (
            max_idle_timeouts
        )
        self.stop_on_server_error = bool(
            stop_on_server_error
        )

    def to_dict(
        self,
    ):
        return {
            "max_requests": (
                self.max_requests
            ),
            "max_idle_timeouts": (
                self.max_idle_timeouts
            ),
            "stop_on_server_error": (
                self.stop_on_server_error
            ),
        }
