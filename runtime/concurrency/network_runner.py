class ConcurrentTCPRunner:
    """
    Bridges Folder 61's synchronous TCPServer with the handwritten WorkerPool.

    Each submitted accept loop handles one connection. This keeps networking
    simple while allowing multiple accepted connections to be served in
    parallel by the runtime concurrency layer.
    """

    def __init__(
        self,
        server,
        worker_pool,
    ):
        if not isinstance(
            server,
            TCPServer,
        ):
            raise TypeError(
                "server must be TCPServer"
            )

        if not isinstance(
            worker_pool,
            WorkerPool,
        ):
            raise TypeError(
                "worker_pool must be WorkerPool"
            )

        self.server = server
        self.worker_pool = worker_pool

    def serve_connections(
        self,
        connection_count,
        max_frames_per_connection=None,
    ):
        if (
            not isinstance(
                connection_count,
                int,
            )
            or connection_count <= 0
        ):
            raise ValueError(
                "connection_count must be positive int"
            )

        futures = []

        index = 0

        while index < connection_count:
            futures.append(
                self.worker_pool.submit(
                    self.server.serve_once,
                    max_frames=(
                        max_frames_per_connection
                    ),
                )
            )

            index += 1

        return futures
