class HostGatewayDispatcher:
    """
    APIGateway-compatible callable dispatcher backed by ServiceHost.
    """

    def __init__(
        self,
        host,
    ):
        if not isinstance(
            host,
            ServiceHost,
        ):
            raise TypeError(
                "host must be ServiceHost"
            )

        self.host = host

    def __call__(
        self,
        request,
    ):
        return self.host.dispatch(
            request
        )
