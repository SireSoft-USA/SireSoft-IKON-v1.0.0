SERIAL_BASE = "libs/core/serialization/"
PROTOCOL_BASE = "libs/protocol/"
GATEWAY_BASE = "services/api_gateway/"

namespace = {
    "__builtins__": __builtins__,
}

for filename in [
    "binary_writer.py",
    "binary_reader.py",
    "checksum.py",
]:
    path = SERIAL_BASE + filename
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
    "error.py",
    "message.py",
    "request.py",
    "response.py",
    "validator.py",
    "codec.py",
]:
    path = PROTOCOL_BASE + filename
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
    "route.py",
    "router.py",
    "middleware.py",
    "gateway.py",
    "routes.py",
]:
    path = GATEWAY_BASE + filename
    source = open(
        path,
        "r",
        encoding="utf-8",
    ).read()

    if "import " in source:
        raise AssertionError(
            "api_gateway implementation contains forbidden import: "
            + filename
        )

    exec(
        compile(
            source,
            path,
            "exec",
        ),
        namespace,
    )

globals().update(namespace)

ASSERTIONS = 0


def check(condition, message):
    global ASSERTIONS
    ASSERTIONS += 1

    if not condition:
        raise AssertionError(message)


def eq(actual, expected, message):
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
    except Exception as exc:
        raise AssertionError(
            message
            + " | wrong exception="
            + repr(exc)
        )

    raise AssertionError(
        message
        + " | expected exception was not raised"
    )


def test_route_and_router():
    router = GatewayRouter()

    route = GatewayRoute(
        "post",
        "/v1/test",
        "test_service",
        "run",
        auth_required=True,
        tags=["test"],
    )

    router.add(route)

    eq(
        route.method,
        "POST",
        "route method normalized",
    )

    eq(
        router.count(),
        1,
        "router count",
    )

    eq(
        router.resolve(
            "POST",
            "/v1/test",
        ).operation,
        "run",
        "route resolution",
    )

    eq(
        router.resolve(
            "GET",
            "/v1/test",
        ),
        None,
        "method-sensitive routing",
    )


def test_duplicate_route_rejected():
    router = GatewayRouter()

    route = GatewayRoute(
        "GET",
        "/health",
        "monitoring_service",
        "health",
    )

    router.add(route)

    expect_error(
        ValueError,
        lambda: router.add(
            GatewayRoute(
                "GET",
                "/health",
                "other",
                "x",
            )
        ),
        "duplicate route rejected",
    )


def test_authentication_middleware():
    route = GatewayRoute(
        "POST",
        "/secure",
        "x",
        "run",
        auth_required=True,
    )

    context = GatewayContext(
        "POST",
        "/secure",
        authenticated=False,
    )

    context.route = route

    error = AuthenticationMiddleware().before(
        context
    )

    eq(
        error.code,
        "UNAUTHENTICATED",
        "auth middleware rejects unauthenticated request",
    )


def test_payload_limit():
    route = GatewayRoute(
        "POST",
        "/small",
        "x",
        "run",
        max_payload_bytes=10,
    )

    context = GatewayContext(
        "POST",
        "/small",
        payload={
            "text": "x" * 100,
        },
    )

    context.route = route

    error = PayloadLimitMiddleware().before(
        context
    )

    eq(
        error.code,
        "PAYLOAD_TOO_LARGE",
        "payload limit enforced",
    )


def test_not_found():
    gateway = APIGateway(
        router=GatewayRouter(),
        dispatcher=lambda request: None,
    )

    response = gateway.handle(
        GatewayContext(
            "GET",
            "/missing",
        )
    )

    eq(
        response["status"],
        404,
        "missing route status",
    )

    eq(
        response["error"]["code"],
        "ROUTE_NOT_FOUND",
        "missing route error",
    )


def test_dispatch_success():
    captured = {
        "request": None,
    }

    def dispatcher(request):
        captured["request"] = request

        return ServiceResponse.success_response(
            request,
            data={
                "answer": "ok",
            },
        )

    gateway = APIGateway(
        dispatcher=dispatcher,
    )

    gateway.register_route(
        GatewayRoute(
            "POST",
            "/v1/chat",
            "rag_service",
            "answer",
        )
    )

    response = gateway.handle(
        GatewayContext(
            "POST",
            "/v1/chat",
            payload={
                "query": "What does SireSoft do?",
            },
            headers={
                "x-client": "test",
            },
            trace_id="trace-1",
            correlation_id="conversation-1",
        )
    )

    eq(
        response["status"],
        200,
        "gateway success status",
    )

    eq(
        response["data"]["answer"],
        "ok",
        "gateway success data",
    )

    request = captured["request"]

    eq(
        request.service,
        "rag_service",
        "gateway routes target service",
    )

    eq(
        request.operation,
        "answer",
        "gateway routes target operation",
    )

    eq(
        request.payload["query"],
        "What does SireSoft do?",
        "gateway payload propagated",
    )

    eq(
        request.trace_id,
        "trace-1",
        "trace propagated",
    )

    eq(
        request.correlation_id,
        "conversation-1",
        "correlation propagated",
    )

    eq(
        request.metadata["headers"]["x-client"],
        "test",
        "gateway headers become metadata",
    )


def test_dispatch_error_mapping():
    def dispatcher(request):
        return ServiceResponse.error_response(
            request,
            ProtocolError(
                code="RATE_LIMITED",
                message="Too many requests",
                retryable=True,
            ),
        )

    gateway = APIGateway(
        dispatcher=dispatcher,
    ).register_route(
        GatewayRoute(
            "POST",
            "/v1/chat",
            "rag_service",
            "answer",
        )
    )

    response = gateway.handle(
        GatewayContext(
            "POST",
            "/v1/chat",
        )
    )

    eq(
        response["status"],
        429,
        "service error mapped to public status",
    )

    eq(
        response["error"]["code"],
        "RATE_LIMITED",
        "service error preserved",
    )


def test_unauthenticated_route_block():
    called = {
        "value": False,
    }

    def dispatcher(request):
        called["value"] = True

        return ServiceResponse.success_response(
            request
        )

    gateway = APIGateway(
        dispatcher=dispatcher,
    ).register_route(
        GatewayRoute(
            "POST",
            "/v1/generate",
            "inference_service",
            "generate",
            auth_required=True,
        )
    )

    response = gateway.handle(
        GatewayContext(
            "POST",
            "/v1/generate",
            authenticated=False,
        )
    )

    eq(
        response["status"],
        401,
        "unauthenticated public status",
    )

    eq(
        called["value"],
        False,
        "middleware stops dispatcher",
    )


def test_authenticated_route_success():
    def dispatcher(request):
        return ServiceResponse.success_response(
            request,
            data={
                "token": 7,
            },
        )

    gateway = APIGateway(
        dispatcher=dispatcher,
    ).register_route(
        GatewayRoute(
            "POST",
            "/v1/generate",
            "inference_service",
            "generate",
            auth_required=True,
        )
    )

    response = gateway.handle(
        GatewayContext(
            "POST",
            "/v1/generate",
            authenticated=True,
        )
    )

    eq(
        response["status"],
        200,
        "authenticated route succeeds",
    )


def test_missing_dispatcher():
    gateway = APIGateway(
        dispatcher=None,
    ).register_route(
        GatewayRoute(
            "GET",
            "/v1/health",
            "monitoring_service",
            "health",
        )
    )

    response = gateway.handle(
        GatewayContext(
            "GET",
            "/v1/health",
        )
    )

    eq(
        response["status"],
        503,
        "missing dispatcher status",
    )

    eq(
        response["error"]["code"],
        "DISPATCHER_UNAVAILABLE",
        "missing dispatcher error",
    )


def test_middleware_after_reverse_order():
    order = []

    class First(GatewayMiddleware):
        def before(self, context):
            order.append("first-before")

        def after(self, context, response):
            order.append("first-after")
            return response

    class Second(GatewayMiddleware):
        def before(self, context):
            order.append("second-before")

        def after(self, context, response):
            order.append("second-after")
            return response

    def dispatcher(request):
        return ServiceResponse.success_response(
            request
        )

    gateway = APIGateway(
        middleware=[
            First(),
            Second(),
        ],
        dispatcher=dispatcher,
    ).register_route(
        GatewayRoute(
            "GET",
            "/x",
            "test_service",
            "run",
        )
    )

    gateway.handle(
        GatewayContext(
            "GET",
            "/x",
        )
    )

    eq(
        order,
        [
            "first-before",
            "second-before",
            "second-after",
            "first-after",
        ],
        "middleware after hooks execute in reverse order",
    )


def test_default_routes():
    router = build_default_router()

    eq(
        router.count(),
        5,
        "default route count",
    )

    eq(
        router.resolve(
            "POST",
            "/v1/chat",
        ).service,
        "rag_service",
        "chat route target",
    )

    eq(
        router.resolve(
            "GET",
            "/v1/health",
        ).service,
        "monitoring_service",
        "health route target",
    )


def test_protocol_compatibility():
    captured = {
        "request": None,
    }

    def dispatcher(request):
        captured["request"] = request

        # Prove gateway-created request is valid under the real protocol.
        validator = ProtocolValidator()

        eq(
            validator.validate_request(
                request
            ),
            [],
            "gateway creates valid ServiceRequest",
        )

        codec = ProtocolCodec()

        round_trip = codec.decode_request(
            codec.encode_request(
                request
            )
        )

        eq(
            round_trip.to_dict(),
            request.to_dict(),
            "gateway request survives real protocol codec",
        )

        return ServiceResponse.success_response(
            request,
            data={
                "ok": True,
            },
        )

    gateway = APIGateway(
        dispatcher=dispatcher,
    ).register_route(
        GatewayRoute(
            "POST",
            "/v1/retrieve",
            "retrieval_service",
            "search",
        )
    )

    response = gateway.handle(
        GatewayContext(
            "POST",
            "/v1/retrieve",
            payload={
                "query": "software",
            },
        )
    )

    eq(
        response["status"],
        200,
        "protocol-compatible gateway dispatch succeeds",
    )


def test_validation():
    expect_error(
        ValueError,
        lambda: GatewayRoute(
            "GET",
            "missing-slash",
            "x",
            "y",
        ),
        "invalid path rejected",
    )

    expect_error(
        TypeError,
        lambda: APIGateway().handle(
            {}
        ),
        "non-context request rejected",
    )

    expect_error(
        ValueError,
        lambda: GatewayContext(
            "",
            "/x",
        ),
        "empty method rejected",
    )


def main():
    test_route_and_router()
    test_duplicate_route_rejected()
    test_authentication_middleware()
    test_payload_limit()
    test_not_found()
    test_dispatch_success()
    test_dispatch_error_mapping()
    test_unauthenticated_route_block()
    test_authenticated_route_success()
    test_missing_dispatcher()
    test_middleware_after_reverse_order()
    test_default_routes()
    test_protocol_compatibility()
    test_validation()

    print(
        "API GATEWAY TEST SUITE: PASS"
    )
    print(
        "Assertions passed:",
        ASSERTIONS,
    )
    print(
        "Files validated: 5/5"
    )
    print(
        "Route registry/resolution: VALIDATED"
    )
    print(
        "Auth + payload middleware: VALIDATED"
    )
    print(
        "Protocol request translation: VALIDATED"
    )
    print(
        "Trace/correlation propagation: VALIDATED"
    )
    print(
        "Service dispatch/error mapping: VALIDATED"
    )
    print(
        "Default SireLLM API contracts: VALIDATED"
    )
    print(
        "Real protocol codec compatibility: VALIDATED"
    )
    print(
        "Third-party dependencies: 0"
    )


main()
