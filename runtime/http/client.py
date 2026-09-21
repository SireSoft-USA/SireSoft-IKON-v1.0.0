import socket


class RawHTTPClient:
    """
    Minimal client used for local runtime/service integration.
    """

    def __init__(
        self,
        host,
        port,
        timeout_seconds=5.0,
        recv_chunk_bytes=4096,
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

        self.host = host
        self.port = port
        self.timeout_seconds = float(
            timeout_seconds
        )
        self.recv_chunk_bytes = (
            recv_chunk_bytes
        )

    def request(
        self,
        method,
        target,
        body=b"",
        headers=None,
    ):
        if not isinstance(
            method,
            str,
        ) or method == "":
            raise ValueError(
                "method must be non-empty str"
            )

        if not isinstance(
            target,
            str,
        ) or not target.startswith(
            "/"
        ):
            raise ValueError(
                "target must start with /"
            )

        if not isinstance(
            body,
            (bytes, bytearray),
        ):
            raise TypeError(
                "body must be bytes-like"
            )

        if headers is None:
            headers = {}

        if not isinstance(
            headers,
            dict,
        ):
            raise TypeError(
                "headers must be dict or None"
            )

        normalized = {}

        for key in headers:
            normalized[
                key.lower()
            ] = str(
                headers[
                    key
                ]
            )

        normalized[
            "host"
        ] = normalized.get(
            "host",
            self.host,
        )

        normalized[
            "content-length"
        ] = str(
            len(
                body
            )
        )

        normalized[
            "connection"
        ] = "close"

        lines = [
            (
                method.upper()
                + " "
                + target
                + " HTTP/1.1\r\n"
            )
        ]

        keys = list(
            normalized.keys()
        )
        keys.sort()

        for key in keys:
            lines.append(
                key
                + ": "
                + normalized[
                    key
                ]
                + "\r\n"
            )

        lines.append(
            "\r\n"
        )

        request_bytes = (
            "".join(
                lines
            ).encode(
                "iso-8859-1"
            )
            + bytes(
                body
            )
        )

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

            sock.sendall(
                request_bytes
            )

            response = b""

            while True:
                chunk = sock.recv(
                    self.recv_chunk_bytes
                )

                if not chunk:
                    break

                response += chunk

        finally:
            sock.close()

        return self._parse_response(
            response
        )

    def _parse_response(
        self,
        data,
    ):
        marker = data.find(
            b"\r\n\r\n"
        )

        if marker < 0:
            raise ValueError(
                "incomplete HTTP response"
            )

        head = data[
            :marker
        ].decode(
            "iso-8859-1"
        )

        body = data[
            marker + 4:
        ]

        lines = head.split(
            "\r\n"
        )

        parts = lines[
            0
        ].split(
            " ",
            2,
        )

        if len(
            parts
        ) < 2:
            raise ValueError(
                "malformed HTTP response status line"
            )

        status = int(
            parts[
                1
            ]
        )

        headers = {}

        for line in lines[
            1:
        ]:
            separator = line.find(
                ":"
            )

            if separator <= 0:
                raise ValueError(
                    "malformed HTTP response header"
                )

            headers[
                line[
                    :separator
                ].strip().lower()
            ] = (
                line[
                    separator + 1:
                ].strip()
            )

        expected = int(
            headers.get(
                "content-length",
                "0",
            )
        )

        if len(
            body
        ) != expected:
            raise ValueError(
                "HTTP response body length mismatch"
            )

        return {
            "status": status,
            "headers": headers,
            "body": body,
        }
