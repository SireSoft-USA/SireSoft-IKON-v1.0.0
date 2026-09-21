import socket


class FrameTransport:
    """
    Four-byte big-endian length framing over a connected TCP socket.
    """

    HEADER_BYTES = 4

    @classmethod
    def send_frame(
        cls,
        sock,
        payload,
        max_frame_bytes=16 * 1024 * 1024,
    ):
        if not isinstance(
            payload,
            (bytes, bytearray),
        ):
            raise TypeError(
                "frame payload must be bytes-like"
            )

        data = bytes(
            payload
        )

        if len(data) > max_frame_bytes:
            raise ValueError(
                "frame exceeds max_frame_bytes"
            )

        header = len(
            data
        ).to_bytes(
            cls.HEADER_BYTES,
            "big",
            signed=False,
        )

        sock.sendall(
            header
            + data
        )

    @classmethod
    def receive_frame(
        cls,
        sock,
        max_frame_bytes=16 * 1024 * 1024,
    ):
        header = cls._recv_exact_or_eof(
            sock,
            cls.HEADER_BYTES,
        )

        if header is None:
            return None

        size = int.from_bytes(
            header,
            "big",
            signed=False,
        )

        if size > max_frame_bytes:
            raise ValueError(
                "incoming frame exceeds max_frame_bytes"
            )

        if size == 0:
            return b""

        payload = cls._recv_exact_or_eof(
            sock,
            size,
        )

        if payload is None:
            raise ConnectionError(
                "connection closed during frame payload"
            )

        return payload

    @classmethod
    def _recv_exact_or_eof(
        cls,
        sock,
        size,
    ):
        chunks = []
        remaining = size

        while remaining > 0:
            chunk = sock.recv(
                remaining
            )

            if not chunk:
                if remaining == size:
                    return None

                raise ConnectionError(
                    "connection closed during frame header/payload"
                )

            chunks.append(
                chunk
            )

            remaining -= len(
                chunk
            )

        return b"".join(
            chunks
        )


class TCPServer:
    """
    Synchronous length-prefixed TCP server.

    Concurrency intentionally belongs to runtime/concurrency. This networking
    layer handles one accepted connection at a time and may process multiple
    frames on that connection.
    """

    def __init__(
        self,
        host,
        port,
        handler,
        backlog=64,
        timeout_seconds=5.0,
        max_frame_bytes=16 * 1024 * 1024,
    ):
        if not isinstance(
            host,
            str,
        ):
            raise TypeError(
                "host must be str"
            )

        if (
            not isinstance(
                port,
                int,
            )
            or port < 0
            or port > 65535
        ):
            raise ValueError(
                "port must be int 0..65535"
            )

        if not callable(
            handler
        ):
            raise TypeError(
                "handler must be callable"
            )

        if (
            not isinstance(
                backlog,
                int,
            )
            or backlog <= 0
        ):
            raise ValueError(
                "backlog must be positive int"
            )

        if (
            not isinstance(
                timeout_seconds,
                (int, float),
            )
            or timeout_seconds <= 0
        ):
            raise ValueError(
                "timeout_seconds must be positive"
            )

        self.host = host
        self.port = port
        self.handler = handler
        self.backlog = backlog
        self.timeout_seconds = float(
            timeout_seconds
        )
        self.max_frame_bytes = (
            max_frame_bytes
        )

        self._socket = None
        self._running = False
        self.accepted_connections = 0
        self.processed_frames = 0
        self.failed_frames = 0

    def start(
        self,
    ):
        if self._socket is not None:
            raise RuntimeError(
                "TCP server already started"
            )

        sock = socket.socket(
            socket.AF_INET,
            socket.SOCK_STREAM,
        )

        sock.setsockopt(
            socket.SOL_SOCKET,
            socket.SO_REUSEADDR,
            1,
        )

        sock.bind(
            (
                self.host,
                self.port,
            )
        )

        sock.listen(
            self.backlog
        )

        sock.settimeout(
            self.timeout_seconds
        )

        self._socket = sock
        self._running = True

        self.port = sock.getsockname()[
            1
        ]

        return self

    def serve_once(
        self,
        max_frames=None,
    ):
        if self._socket is None:
            raise RuntimeError(
                "TCP server is not started"
            )

        if max_frames is not None:
            if (
                not isinstance(
                    max_frames,
                    int,
                )
                or max_frames <= 0
            ):
                raise ValueError(
                    "max_frames must be positive int or None"
                )

        connection, address = (
            self._socket.accept()
        )

        self.accepted_connections += 1

        connection.settimeout(
            self.timeout_seconds
        )

        frames = 0

        try:
            while self._running:
                payload = (
                    FrameTransport
                    .receive_frame(
                        connection,
                        self.max_frame_bytes,
                    )
                )

                if payload is None:
                    break

                try:
                    response = self.handler(
                        payload,
                        address,
                    )

                    if not isinstance(
                        response,
                        (bytes, bytearray),
                    ):
                        raise TypeError(
                            "TCP handler must return bytes-like response"
                        )

                    FrameTransport.send_frame(
                        connection,
                        response,
                        self.max_frame_bytes,
                    )

                    self.processed_frames += 1
                    frames += 1

                except Exception:
                    self.failed_frames += 1
                    raise

                if (
                    max_frames is not None
                    and frames >= max_frames
                ):
                    break

        finally:
            connection.close()

        return {
            "address": address,
            "frames": frames,
        }

    def stop(
        self,
    ):
        self._running = False

        if self._socket is not None:
            self._socket.close()
            self._socket = None

        return self

    def status(
        self,
    ):
        return {
            "running": (
                self._socket
                is not None
                and self._running
            ),
            "host": self.host,
            "port": self.port,
            "accepted_connections": (
                self.accepted_connections
            ),
            "processed_frames": (
                self.processed_frames
            ),
            "failed_frames": (
                self.failed_frames
            ),
            "max_frame_bytes": (
                self.max_frame_bytes
            ),
        }


class ProtocolTCPHandler:
    """
    Adapter from raw TCP frame bytes to existing SireLLM ServiceRequest /
    ServiceResponse protocol objects.
    """

    def __init__(
        self,
        protocol_codec,
        dispatcher,
    ):
        if protocol_codec is None:
            raise TypeError(
                "protocol_codec is required"
            )

        if not callable(
            dispatcher
        ):
            raise TypeError(
                "dispatcher must be callable"
            )

        self.protocol_codec = (
            protocol_codec
        )
        self.dispatcher = (
            dispatcher
        )

    def __call__(
        self,
        payload,
        address=None,
    ):
        request = (
            self.protocol_codec
            .decode_request(
                payload
            )
        )

        response = self.dispatcher(
            request
        )

        if not isinstance(
            response,
            ServiceResponse,
        ):
            raise TypeError(
                "dispatcher must return ServiceResponse"
            )

        return (
            self.protocol_codec
            .encode_response(
                response
            )
        )
