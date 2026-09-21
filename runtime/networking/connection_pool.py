import socket


class TCPConnectionPool:
    """
    Small reusable TCP connection pool.

    The pool owns raw sockets. A checked-out connection must be released or
    discarded explicitly. Reuse is appropriate only when the remote server
    supports multiple framed requests per connection.
    """

    def __init__(
        self,
        host,
        port,
        max_size=4,
        timeout_seconds=5.0,
        max_frame_bytes=16 * 1024 * 1024,
    ):
        if not isinstance(
            host,
            str,
        ) or host == "":
            raise ValueError(
                "host must be non-empty str"
            )

        if (
            not isinstance(
                port,
                int,
            )
            or port <= 0
            or port > 65535
        ):
            raise ValueError(
                "port must be int 1..65535"
            )

        if (
            not isinstance(
                max_size,
                int,
            )
            or max_size <= 0
        ):
            raise ValueError(
                "max_size must be positive int"
            )

        self.host = host
        self.port = port
        self.max_size = max_size
        self.timeout_seconds = float(
            timeout_seconds
        )
        self.max_frame_bytes = (
            max_frame_bytes
        )

        self._idle = []
        self._leased = {}
        self._created = 0
        self._closed = False

        self.total_acquires = 0
        self.total_reuses = 0
        self.total_discards = 0

    def acquire(
        self,
    ):
        if self._closed:
            raise RuntimeError(
                "connection pool is closed"
            )

        if len(
            self._idle
        ) > 0:
            sock = self._idle.pop()

            self.total_reuses += 1

        else:
            if self._created >= self.max_size:
                raise RuntimeError(
                    "connection pool exhausted"
                )

            sock = socket.socket(
                socket.AF_INET,
                socket.SOCK_STREAM,
            )

            sock.settimeout(
                self.timeout_seconds
            )

            sock.connect(
                (
                    self.host,
                    self.port,
                )
            )

            self._created += 1

        identifier = id(
            sock
        )

        self._leased[
            identifier
        ] = sock

        self.total_acquires += 1

        return sock

    def release(
        self,
        sock,
    ):
        identifier = id(
            sock
        )

        if identifier not in self._leased:
            raise ValueError(
                "socket is not leased from this pool"
            )

        del self._leased[
            identifier
        ]

        if self._closed:
            sock.close()
            self._created -= 1
            return

        self._idle.append(
            sock
        )

    def discard(
        self,
        sock,
    ):
        identifier = id(
            sock
        )

        if identifier in self._leased:
            del self._leased[
                identifier
            ]

        else:
            index = 0
            found = False

            while index < len(
                self._idle
            ):
                if self._idle[
                    index
                ] is sock:
                    del self._idle[
                        index
                    ]
                    found = True
                    break

                index += 1

            if not found:
                raise ValueError(
                    "socket does not belong to this pool"
                )

        try:
            sock.close()
        finally:
            self._created -= 1
            self.total_discards += 1

    def request(
        self,
        payload,
    ):
        sock = self.acquire()

        try:
            FrameTransport.send_frame(
                sock,
                payload,
                self.max_frame_bytes,
            )

            response = (
                FrameTransport
                .receive_frame(
                    sock,
                    self.max_frame_bytes,
                )
            )

            if response is None:
                raise ConnectionError(
                    "server closed without response"
                )

            self.release(
                sock
            )

            return response

        except Exception:
            try:
                self.discard(
                    sock
                )
            except Exception:
                pass

            raise

    def close(
        self,
    ):
        self._closed = True

        for sock in list(
            self._idle
        ):
            try:
                sock.close()
            finally:
                self._created -= 1

        self._idle = []

        # Leased sockets are deliberately not force-closed. They will be closed
        # when returned after pool closure.

        return self

    def status(
        self,
    ):
        return {
            "host": self.host,
            "port": self.port,
            "max_size": self.max_size,
            "created": self._created,
            "idle": len(
                self._idle
            ),
            "leased": len(
                self._leased
            ),
            "closed": self._closed,
            "total_acquires": (
                self.total_acquires
            ),
            "total_reuses": (
                self.total_reuses
            ),
            "total_discards": (
                self.total_discards
            ),
        }
