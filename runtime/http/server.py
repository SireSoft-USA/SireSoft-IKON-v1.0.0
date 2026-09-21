import socket


class RawHTTPServer:
    """
    Small synchronous HTTP/1.0-1.1 server for the transport adapter.

    One request is processed per accepted connection and responses always use
    Connection: close. Transfer-Encoding is not supported by Folder 61's strict
    HTTP parser.
    """

    def __init__(
        self,
        host,
        port,
        adapter,
        parser=None,
        backlog=64,
        timeout_seconds=5.0,
        recv_chunk_bytes=4096,
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

        if not isinstance(
            adapter,
            HTTPGatewayAdapter,
        ):
            raise TypeError(
                "adapter must be HTTPGatewayAdapter"
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

        if (
            not isinstance(
                recv_chunk_bytes,
                int,
            )
            or recv_chunk_bytes <= 0
        ):
            raise ValueError(
                "recv_chunk_bytes must be positive int"
            )

        self.host = host
        self.port = port
        self.adapter = adapter
        self.parser = (
            HTTPParser()
            if parser is None
            else parser
        )
        self.backlog = backlog
        self.timeout_seconds = float(
            timeout_seconds
        )
        self.recv_chunk_bytes = (
            recv_chunk_bytes
        )

        self._socket = None
        self._running = False

        self.accepted_connections = 0
        self.completed_requests = 0
        self.bad_requests = 0
        self.failed_requests = 0

    def start(
        self,
    ):
        if self._socket is not None:
            raise RuntimeError(
                "HTTP server already started"
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

        self.port = (
            sock.getsockname()[
                1
            ]
        )

        return self

    def serve_once(
        self,
    ):
        if self._socket is None:
            raise RuntimeError(
                "HTTP server is not started"
            )

        connection, address = (
            self._socket.accept()
        )

        self.accepted_connections += 1

        connection.settimeout(
            self.timeout_seconds
        )

        try:
            try:
                raw = self._read_request(
                    connection
                )

                request = (
                    self.parser
                    .parse_request(
                        raw
                    )
                )

                response = (
                    self.adapter
                    .handle(
                        request
                    )
                )

                self.completed_requests += 1

            except (
                ValueError,
                TypeError,
            ) as error:
                self.bad_requests += 1

                response = (
                    self.adapter
                    .error_response(
                        400,
                        "BAD_HTTP_REQUEST",
                        str(
                            error
                        ),
                    )
                )

            except Exception:
                self.failed_requests += 1

                response = (
                    self.adapter
                    .error_response(
                        500,
                        "HTTP_SERVER_ERROR",
                        (
                            "Internal HTTP transport error"
                        ),
                    )
                )

            connection.sendall(
                response.to_bytes()
            )

        finally:
            connection.close()

        return {
            "address": address,
            "status": (
                response.status_code
            ),
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
                self._running
                and self._socket
                is not None
            ),
            "host": self.host,
            "port": self.port,
            "accepted_connections": (
                self.accepted_connections
            ),
            "completed_requests": (
                self.completed_requests
            ),
            "bad_requests": (
                self.bad_requests
            ),
            "failed_requests": (
                self.failed_requests
            ),
        }

    def _read_request(
        self,
        connection,
    ):
        data = b""

        marker = -1

        while marker < 0:
            chunk = connection.recv(
                self.recv_chunk_bytes
            )

            if not chunk:
                raise ValueError(
                    "connection closed before HTTP headers completed"
                )

            data += chunk

            marker = data.find(
                b"\r\n\r\n"
            )

            if (
                marker < 0
                and len(
                    data
                )
                > self.parser
                .max_header_bytes
            ):
                raise ValueError(
                    "HTTP headers exceed max_header_bytes"
                )

        header_end = marker + 4

        if header_end > self.parser.max_header_bytes:
            raise ValueError(
                "HTTP headers exceed max_header_bytes"
            )

        expected_body = (
            self._content_length(
                data[
                    :marker
                ]
            )
        )

        if expected_body > self.parser.max_body_bytes:
            raise ValueError(
                "HTTP body exceeds max_body_bytes"
            )

        total = (
            header_end
            + expected_body
        )

        if len(
            data
        ) > total:
            raise ValueError(
                "unexpected bytes after HTTP request body"
            )

        while len(
            data
        ) < total:
            chunk = connection.recv(
                min(
                    self.recv_chunk_bytes,
                    total
                    - len(
                        data
                    ),
                )
            )

            if not chunk:
                raise ValueError(
                    "connection closed before HTTP body completed"
                )

            data += chunk

        return data

    def _content_length(
        self,
        head,
    ):
        try:
            text = head.decode(
                "iso-8859-1"
            )

        except UnicodeDecodeError:
            raise ValueError(
                "invalid HTTP header encoding"
            )

        lines = text.split(
            "\r\n"
        )

        content_length = None

        for line in lines[
            1:
        ]:
            separator = line.find(
                ":"
            )

            if separator <= 0:
                raise ValueError(
                    "malformed HTTP header"
                )

            name = (
                line[
                    :separator
                ]
                .strip()
                .lower()
            )

            value = (
                line[
                    separator + 1:
                ]
                .strip()
            )

            if name == "transfer-encoding":
                raise ValueError(
                    "Transfer-Encoding is not supported"
                )

            if name == "content-length":
                if content_length is not None:
                    raise ValueError(
                        "duplicate Content-Length"
                    )

                try:
                    content_length = int(
                        value
                    )

                except ValueError:
                    raise ValueError(
                        "invalid Content-Length"
                    )

                if content_length < 0:
                    raise ValueError(
                        "Content-Length cannot be negative"
                    )

        if content_length is None:
            return 0

        return content_length
