import socket


class TCPClient:
    """
    One-request-per-connection TCP client using FrameTransport framing.
    """

    def __init__(
        self,
        host,
        port,
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
        self.timeout_seconds = float(
            timeout_seconds
        )
        self.max_frame_bytes = (
            max_frame_bytes
        )

        self.requests = 0
        self.failures = 0

    def request(
        self,
        payload,
    ):
        sock = socket.socket(
            socket.AF_INET,
            socket.SOCK_STREAM,
        )

        sock.settimeout(
            self.timeout_seconds
        )

        try:
            sock.connect(
                (
                    self.host,
                    self.port,
                )
            )

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

            self.requests += 1

            return response

        except Exception:
            self.failures += 1
            raise

        finally:
            sock.close()

    def status(
        self,
    ):
        return {
            "host": self.host,
            "port": self.port,
            "requests": self.requests,
            "failures": self.failures,
            "max_frame_bytes": (
                self.max_frame_bytes
            ),
        }


class ProtocolTCPClient:
    """
    Typed client wrapper over the existing SireLLM ProtocolCodec.
    """

    def __init__(
        self,
        tcp_client,
        protocol_codec,
    ):
        if not isinstance(
            tcp_client,
            TCPClient,
        ):
            raise TypeError(
                "tcp_client must be TCPClient"
            )

        if protocol_codec is None:
            raise TypeError(
                "protocol_codec is required"
            )

        self.tcp_client = tcp_client
        self.protocol_codec = (
            protocol_codec
        )

    def request(
        self,
        service_request,
    ):
        encoded = (
            self.protocol_codec
            .encode_request(
                service_request
            )
        )

        response_bytes = (
            self.tcp_client
            .request(
                encoded
            )
        )

        return (
            self.protocol_codec
            .decode_response(
                response_bytes
            )
        )
