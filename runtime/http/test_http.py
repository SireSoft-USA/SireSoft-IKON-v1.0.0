import threading

PARSERS_BASE = "libs/data/parsers/"
PROTOCOL_BASE = "libs/protocol/"
GATEWAY_BASE = "services/api_gateway/"
NETWORK_BASE = "runtime/networking/"
HTTP_BASE = "runtime/http/"

namespace = {
    "__builtins__": __builtins__,
}

groups = [
    (
        PARSERS_BASE,
        [
            "json_parser.py",
        ],
    ),
    (
        PROTOCOL_BASE,
        [
            "error.py",
            "message.py",
            "request.py",
            "response.py",
            "validator.py",
            "codec.py",
        ],
    ),
    (
        GATEWAY_BASE,
        [
            "middleware.py",
            "route.py",
            "router.py",
            "gateway.py",
            "routes.py",
        ],
    ),
    (
        NETWORK_BASE,
        [
            "http_parser.py",
        ],
    ),
]

for base, filenames in groups:
    for filename in filenames:
        path = base + filename

        source = open(
            path,
            "r",
            encoding="utf-8",
        ).read()

        exec(
            compile(
                source,
                path,
                "exec",
            ),
            namespace,
        )

for filename in [
    "json_codec.py",
    "gateway_adapter.py",
    "server.py",
    "client.py",
]:
    path = HTTP_BASE + filename

    source = open(
        path,
        "r",
        encoding="utf-8",
    ).read()

    exec(
        compile(
            source,
            path,
            "exec",
        ),
        namespace,
    )

globals().update(
    namespace
)

ASSERTIONS = 0


def check(
    condition,
    message,
):
    global ASSERTIONS
    ASSERTIONS += 1

    if not condition:
        raise AssertionError(
            message
        )


def eq(
    actual,
    expected,
    message,
):
    check(
        actual == expected,
        message
        + " | got="
        + repr(actual)
        + " expected="
        + repr(expected)
    )


def expect_error(
    error_type,
    fn,
    message,
):
    global ASSERTIONS
    ASSERTIONS += 1

    try:
        fn()

    except error_type:
        return

    except Exception as error:
        raise AssertionError(
            message
            + " | wrong exception="
            + repr(error)
        )

    raise AssertionError(
        message
        + " | expected exception was not raised"
    )


def gateway(
    auth_required=False,
):
    router = GatewayRouter()

    router.add(
        GatewayRoute(
            "POST",
            "/v1/echo",
            "echo_service",
            "echo",
            auth_required=(
                auth_required
            ),
            max_payload_bytes=1024,
        )
    )

    router.add(
        GatewayRoute(
            "GET",
            "/v1/health",
            "monitoring_service",
            "health",
            auth_required=False,
            max_payload_bytes=1024,
        )
    )

    def dispatch(
        request,
    ):
        if request.service == "echo_service":
            return (
                ServiceResponse
                .success_response(
                    request,
                    data={
                        "echo": (
                            request.payload
                        ),
                        "correlation_id": (
                            request.correlation_id
                        ),
                    },
                )
            )

        if request.service == "monitoring_service":
            return (
                ServiceResponse
                .success_response(
                    request,
                    data={
                        "ready": True,
                    },
                )
            )

        return (
            ServiceResponse
            .error_response(
                request,
                ProtocolError(
                    code="NOT_FOUND",
                    message="service not found",
                    retryable=False,
                ),
            )
        )

    return APIGateway(
        router=router,
        dispatcher=dispatch,
    )


def test_json_codec():
    codec = RuntimeJSONCodec()

    value = {
        "message": (
            "hello\nworld"
        ),
        "ok": True,
        "count": 3,
        "items": [
            None,
            2.5,
        ],
    }

    encoded = codec.encode(
        value
    )

    decoded = codec.decode(
        encoded
    )

    eq(
        decoded,
        value,
        "handwritten JSON codec round trip",
    )

    expect_error(
        ValueError,
        lambda: codec.encode(
            float(
                "nan"
            )
        ),
        "NaN rejected",
    )


def test_adapter_post():
    codec = RuntimeJSONCodec()

    adapter = HTTPGatewayAdapter(
        gateway()
    )

    body = codec.encode({
        "text": "hello",
    })

    request = HTTPRequest(
        method="POST",
        target="/v1/echo?ignored=yes",
        version="HTTP/1.1",
        headers={
            "content-type": (
                "application/json"
            ),
            "x-correlation-id": (
                "corr-1"
            ),
        },
        body=body,
    )

    response = adapter.handle(
        request
    )

    eq(
        response.status_code,
        200,
        "gateway adapter returns HTTP 200",
    )

    public = codec.decode(
        response.body
    )

    eq(
        public[
            "data"
        ][
            "echo"
        ][
            "text"
        ],
        "hello",
        "HTTP JSON payload reaches gateway dispatcher",
    )

    eq(
        public[
            "data"
        ][
            "correlation_id"
        ],
        "corr-1",
        "correlation header reaches ServiceRequest",
    )


def test_adapter_get():
    codec = RuntimeJSONCodec()

    adapter = HTTPGatewayAdapter(
        gateway()
    )

    request = HTTPRequest(
        "GET",
        "/v1/health",
        "HTTP/1.1",
        headers={},
        body=b"",
    )

    response = adapter.handle(
        request
    )

    public = codec.decode(
        response.body
    )

    eq(
        public[
            "data"
        ][
            "ready"
        ],
        True,
        "GET health route works with empty payload",
    )


def test_auth_enricher():
    codec = RuntimeJSONCodec()

    denied = HTTPGatewayAdapter(
        gateway(
            auth_required=True
        )
    )

    request = HTTPRequest(
        "POST",
        "/v1/echo",
        "HTTP/1.1",
        headers={
            "content-type": (
                "application/json"
            ),
        },
        body=codec.encode({
            "x": 1,
        }),
    )

    denied_response = (
        denied.handle(
            request
        )
    )

    eq(
        denied_response.status_code,
        401,
        "transport does not trust authentication headers by default",
    )

    allowed = HTTPGatewayAdapter(
        gateway(
            auth_required=True
        ),
        context_enricher=(
            lambda request: {
                "authenticated": True,
            }
        ),
    )

    eq(
        allowed.handle(
            request
        ).status_code,
        200,
        "trusted context enricher can mark request authenticated",
    )


def test_content_type_rejection():
    adapter = HTTPGatewayAdapter(
        gateway()
    )

    request = HTTPRequest(
        "POST",
        "/v1/echo",
        "HTTP/1.1",
        headers={
            "content-type": (
                "text/plain"
            ),
        },
        body=b"hello",
    )

    expect_error(
        ValueError,
        lambda: adapter.handle(
            request
        ),
        "non-JSON HTTP API body rejected",
    )


def run_once(
    server,
    errors,
):
    try:
        server.serve_once()

    except Exception as error:
        errors.append(
            error
        )


def test_real_http_server_post():
    codec = RuntimeJSONCodec()

    server = RawHTTPServer(
        host="127.0.0.1",
        port=0,
        adapter=HTTPGatewayAdapter(
            gateway()
        ),
        timeout_seconds=3.0,
    )

    server.start()

    errors = []

    thread = threading.Thread(
        target=run_once,
        args=(
            server,
            errors,
        ),
    )

    thread.start()

    client = RawHTTPClient(
        "127.0.0.1",
        server.port,
        timeout_seconds=3.0,
    )

    response = client.request(
        "POST",
        "/v1/echo",
        body=codec.encode({
            "message": "over-http",
        }),
        headers={
            "content-type": (
                "application/json"
            ),
            "x-trace-id": (
                "trace-http"
            ),
        },
    )

    thread.join(
        timeout=5.0
    )

    server.stop()

    eq(
        errors,
        [],
        "raw HTTP server completes without errors",
    )

    eq(
        response[
            "status"
        ],
        200,
        "real socket HTTP POST status",
    )

    public = codec.decode(
        response[
            "body"
        ]
    )

    eq(
        public[
            "data"
        ][
            "echo"
        ][
            "message"
        ],
        "over-http",
        "real socket request reaches API gateway",
    )

    eq(
        public[
            "trace_id"
        ],
        "trace-http",
        "trace header preserved through HTTP gateway",
    )


def test_real_http_server_bad_request():
    server = RawHTTPServer(
        "127.0.0.1",
        0,
        HTTPGatewayAdapter(
            gateway()
        ),
        timeout_seconds=3.0,
    )

    server.start()

    errors = []

    thread = threading.Thread(
        target=run_once,
        args=(
            server,
            errors,
        ),
    )

    thread.start()

    client = RawHTTPClient(
        "127.0.0.1",
        server.port,
        timeout_seconds=3.0,
    )

    response = client.request(
        "POST",
        "/v1/echo",
        body=b"not-json",
        headers={
            "content-type": (
                "application/json"
            ),
        },
    )

    thread.join(
        timeout=5.0
    )

    server.stop()

    eq(
        response[
            "status"
        ],
        400,
        "invalid JSON maps to HTTP 400",
    )

    eq(
        server.status()[
            "bad_requests"
        ],
        1,
        "bad HTTP request count tracked",
    )


def test_route_not_found():
    codec = RuntimeJSONCodec()

    adapter = HTTPGatewayAdapter(
        gateway()
    )

    response = adapter.handle(
        HTTPRequest(
            "GET",
            "/missing",
            "HTTP/1.1",
            headers={},
        )
    )

    eq(
        response.status_code,
        404,
        "gateway route not found maps to HTTP 404",
    )

    public = codec.decode(
        response.body
    )

    eq(
        public[
            "error"
        ][
            "code"
        ],
        "ROUTE_NOT_FOUND",
        "gateway error preserved",
    )


def test_server_status():
    server = RawHTTPServer(
        "127.0.0.1",
        0,
        HTTPGatewayAdapter(
            gateway()
        ),
    )

    server.start()

    check(
        server.status()[
            "running"
        ],
        "HTTP server reports running",
    )

    check(
        server.status()[
            "port"
        ] > 0,
        "HTTP server resolves ephemeral port",
    )

    server.stop()

    eq(
        server.status()[
            "running"
        ],
        False,
        "HTTP server reports stopped",
    )


def main():
    test_json_codec()
    test_adapter_post()
    test_adapter_get()
    test_auth_enricher()
    test_content_type_rejection()
    test_real_http_server_post()
    test_real_http_server_bad_request()
    test_route_not_found()
    test_server_status()

    print(
        "RUNTIME HTTP TEST SUITE: PASS"
    )
    print(
        "Assertions passed:",
        ASSERTIONS,
    )
    print(
        "Files validated: 4/4"
    )
    print(
        "Handwritten JSON transport codec: VALIDATED"
    )
    print(
        "HTTP -> GatewayContext translation: VALIDATED"
    )
    print(
        "APIGateway -> HTTP response translation: VALIDATED"
    )
    print(
        "Real raw-socket HTTP request handling: VALIDATED"
    )
    print(
        "Trace/correlation propagation: VALIDATED"
    )
    print(
        "Trusted authentication enrichment boundary: VALIDATED"
    )
    print(
        "Third-party dependencies: 0"
    )
    print(
        "Standard-library networking dependency: socket"
    )
    print(
        "Test-only concurrency dependency: threading"
    )


main()
