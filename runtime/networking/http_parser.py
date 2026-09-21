class HTTPRequest:
    def __init__(
        self,
        method,
        target,
        version,
        headers=None,
        body=b"",
    ):
        if not isinstance(method, str) or method == "":
            raise ValueError("method must be non-empty str")

        if not isinstance(target, str) or target == "":
            raise ValueError("target must be non-empty str")

        if version not in (
            "HTTP/1.0",
            "HTTP/1.1",
        ):
            raise ValueError("unsupported HTTP version")

        if headers is None:
            headers = {}

        if not isinstance(headers, dict):
            raise TypeError("headers must be dict or None")

        if not isinstance(
            body,
            (bytes, bytearray),
        ):
            raise TypeError("body must be bytes-like")

        self.method = method.upper()
        self.target = target
        self.version = version
        self.headers = self._copy_headers(
            headers
        )
        self.body = bytes(body)

    def header(
        self,
        name,
        default=None,
    ):
        if not isinstance(name, str):
            raise TypeError("header name must be str")

        return self.headers.get(
            name.lower(),
            default,
        )

    def to_dict(
        self,
    ):
        return {
            "method": self.method,
            "target": self.target,
            "version": self.version,
            "headers": dict(
                self.headers
            ),
            "body": self.body,
        }

    def _copy_headers(
        self,
        headers,
    ):
        result = {}

        for key in headers:
            if not isinstance(key, str) or key == "":
                raise ValueError(
                    "header names must be non-empty strings"
                )

            value = headers[key]

            if not isinstance(value, str):
                raise TypeError(
                    "header values must be strings"
                )

            normalized = key.lower()

            if normalized in result:
                raise ValueError(
                    "duplicate HTTP header: "
                    + key
                )

            result[normalized] = value

        return result


class HTTPResponse:
    REASONS = {
        200: "OK",
        201: "Created",
        204: "No Content",
        400: "Bad Request",
        401: "Unauthorized",
        403: "Forbidden",
        404: "Not Found",
        409: "Conflict",
        413: "Payload Too Large",
        429: "Too Many Requests",
        500: "Internal Server Error",
        503: "Service Unavailable",
    }

    def __init__(
        self,
        status_code,
        body=b"",
        headers=None,
        version="HTTP/1.1",
        reason=None,
    ):
        if (
            not isinstance(status_code, int)
            or status_code < 100
            or status_code > 599
        ):
            raise ValueError(
                "status_code must be int 100..599"
            )

        if version not in (
            "HTTP/1.0",
            "HTTP/1.1",
        ):
            raise ValueError("unsupported HTTP version")

        if not isinstance(
            body,
            (bytes, bytearray),
        ):
            raise TypeError("body must be bytes-like")

        if headers is None:
            headers = {}

        if not isinstance(headers, dict):
            raise TypeError("headers must be dict or None")

        if reason is None:
            reason = self.REASONS.get(
                status_code,
                "Unknown",
            )

        if not isinstance(reason, str):
            raise TypeError("reason must be str")

        self.status_code = status_code
        self.body = bytes(body)
        self.version = version
        self.reason = reason

        self.headers = {}

        for key in headers:
            if not isinstance(key, str) or key == "":
                raise ValueError(
                    "header names must be non-empty strings"
                )

            value = headers[key]

            if not isinstance(value, str):
                raise TypeError(
                    "header values must be strings"
                )

            self.headers[
                key.lower()
            ] = value

    def to_bytes(
        self,
    ):
        headers = dict(
            self.headers
        )

        headers[
            "content-length"
        ] = str(
            len(
                self.body
            )
        )

        if "connection" not in headers:
            headers[
                "connection"
            ] = "close"

        start = (
            self.version
            + " "
            + str(
                self.status_code
            )
            + " "
            + self.reason
            + "\r\n"
        )

        lines = [
            start
        ]

        keys = list(
            headers.keys()
        )
        keys.sort()

        for key in keys:
            lines.append(
                key
                + ": "
                + headers[
                    key
                ]
                + "\r\n"
            )

        lines.append(
            "\r\n"
        )

        head = "".join(
            lines
        ).encode(
            "iso-8859-1"
        )

        return (
            head
            + self.body
        )


class HTTPParser:
    """
    Strict HTTP/1.0-1.1 request parser.

    Supported request bodies use Content-Length. Transfer-Encoding/chunked is
    intentionally rejected for now rather than partially or incorrectly parsed.
    """

    def __init__(
        self,
        max_header_bytes=64 * 1024,
        max_body_bytes=8 * 1024 * 1024,
        max_headers=100,
    ):
        if (
            not isinstance(max_header_bytes, int)
            or max_header_bytes <= 0
        ):
            raise ValueError(
                "max_header_bytes must be positive int"
            )

        if (
            not isinstance(max_body_bytes, int)
            or max_body_bytes < 0
        ):
            raise ValueError(
                "max_body_bytes must be non-negative int"
            )

        if (
            not isinstance(max_headers, int)
            or max_headers <= 0
        ):
            raise ValueError(
                "max_headers must be positive int"
            )

        self.max_header_bytes = max_header_bytes
        self.max_body_bytes = max_body_bytes
        self.max_headers = max_headers

    def parse_request(
        self,
        data,
    ):
        if not isinstance(
            data,
            (bytes, bytearray),
        ):
            raise TypeError(
                "HTTP request data must be bytes-like"
            )

        raw = bytes(data)

        marker = raw.find(
            b"\r\n\r\n"
        )

        if marker < 0:
            raise ValueError(
                "incomplete HTTP header block"
            )

        header_end = marker + 4

        if header_end > self.max_header_bytes:
            raise ValueError(
                "HTTP headers exceed max_header_bytes"
            )

        head = raw[
            :marker
        ]

        body = raw[
            header_end:
        ]

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

        if len(lines) == 0 or lines[0] == "":
            raise ValueError(
                "missing HTTP request line"
            )

        request_parts = lines[
            0
        ].split(
            " "
        )

        if len(request_parts) != 3:
            raise ValueError(
                "malformed HTTP request line"
            )

        method = request_parts[0]
        target = request_parts[1]
        version = request_parts[2]

        if method == "" or target == "":
            raise ValueError(
                "HTTP method/target cannot be empty"
            )

        if version not in (
            "HTTP/1.0",
            "HTTP/1.1",
        ):
            raise ValueError(
                "unsupported HTTP version"
            )

        headers = {}

        if len(lines) - 1 > self.max_headers:
            raise ValueError(
                "HTTP header count exceeds max_headers"
            )

        for line in lines[1:]:
            separator = line.find(
                ":"
            )

            if separator <= 0:
                raise ValueError(
                    "malformed HTTP header"
                )

            name = line[
                :separator
            ].strip().lower()

            value = line[
                separator + 1:
            ].strip()

            if name == "":
                raise ValueError(
                    "HTTP header name cannot be empty"
                )

            if name in headers:
                raise ValueError(
                    "duplicate HTTP header: "
                    + name
                )

            headers[
                name
            ] = value

        transfer_encoding = headers.get(
            "transfer-encoding"
        )

        if transfer_encoding is not None:
            raise ValueError(
                "Transfer-Encoding is not supported"
            )

        content_length = headers.get(
            "content-length"
        )

        expected_body = 0

        if content_length is not None:
            try:
                expected_body = int(
                    content_length
                )

            except ValueError:
                raise ValueError(
                    "invalid Content-Length"
                )

            if expected_body < 0:
                raise ValueError(
                    "Content-Length cannot be negative"
                )

        if expected_body > self.max_body_bytes:
            raise ValueError(
                "HTTP body exceeds max_body_bytes"
            )

        if len(body) != expected_body:
            raise ValueError(
                "HTTP body length does not match Content-Length"
            )

        return HTTPRequest(
            method=method,
            target=target,
            version=version,
            headers=headers,
            body=body,
        )
