SERIAL_BASE = "libs/core/serialization/"
PROTOCOL_BASE = "libs/protocol/"
GATEWAY_BASE = "services/api_gateway/"
SERVICE_BASE = "services/rate_limit_service/"

namespace = {
    "__builtins__": __builtins__,
}

groups = [
    (
        SERIAL_BASE,
        [
            "binary_writer.py",
            "binary_reader.py",
            "checksum.py",
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
            "route.py",
            "router.py",
            "middleware.py",
            "gateway.py",
            "routes.py",
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
    "policy.py",
    "bucket.py",
    "manager.py",
    "gateway_adapter.py",
    "service.py",
]:
    path = SERVICE_BASE + filename

    source = open(
        path,
        "r",
        encoding="utf-8",
    ).read()

    if "import " in source:
        raise AssertionError(
            "rate_limit_service implementation contains forbidden import: "
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
        + repr(
            actual
        )
        + " expected="
        + repr(
            expected
        )
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
            + repr(
                error
            )
        )

    raise AssertionError(
        message
        + " | expected exception was not raised"
    )


def manager():
    worker = RateLimitManager()

    worker.configure_policy(
        policy_id="chat",
        capacity=3,
        refill_tokens=1,
        refill_seconds=10,
        cost=1,
    )

    worker.configure_policy(
        policy_id="expensive",
        capacity=10,
        refill_tokens=2,
        refill_seconds=5,
        cost=3,
    )

    return worker


def test_policy_validation():
    policy = RateLimitPolicy(
        "chat",
        5,
        2,
        10,
        cost=1,
        metadata={
            "scope": "chat",
        },
    )

    eq(
        policy.capacity,
        5,
        "policy capacity",
    )

    eq(
        policy.to_dict()[
            "metadata"
        ][
            "scope"
        ],
        "chat",
        "policy metadata",
    )

    restored = RateLimitPolicy.from_dict(
        policy.to_dict()
    )

    eq(
        restored.to_dict(),
        policy.to_dict(),
        "policy state round trip",
    )

    expect_error(
        ValueError,
        lambda: RateLimitPolicy(
            "bad",
            1,
            1,
            1,
            cost=2,
        ),
        "cost over capacity rejected",
    )


def test_bucket_burst_and_denial():
    worker = manager()

    first = worker.consume(
        "chat",
        "user:u1",
        now=100,
    )

    second = worker.consume(
        "chat",
        "user:u1",
        now=100,
    )

    third = worker.consume(
        "chat",
        "user:u1",
        now=100,
    )

    denied = worker.consume(
        "chat",
        "user:u1",
        now=100,
    )

    eq(
        first[
            "remaining_tokens"
        ],
        2,
        "first request consumes one token",
    )

    eq(
        second[
            "remaining_tokens"
        ],
        1,
        "second request consumes one token",
    )

    eq(
        third[
            "remaining_tokens"
        ],
        0,
        "burst capacity exhausted",
    )

    eq(
        denied[
            "allowed"
        ],
        False,
        "request denied after burst",
    )

    eq(
        denied[
            "retry_after_seconds"
        ],
        10,
        "retry-after calculated",
    )


def test_check_does_not_consume():
    worker = manager()

    before = worker.check(
        "chat",
        "user:u1",
        now=100,
    )

    after = worker.check(
        "chat",
        "user:u1",
        now=100,
    )

    eq(
        before[
            "remaining_tokens"
        ],
        3,
        "check sees full bucket",
    )

    eq(
        after[
            "remaining_tokens"
        ],
        3,
        "check does not consume",
    )


def test_refill():
    worker = manager()

    worker.consume(
        "chat",
        "u",
        now=100,
    )

    worker.consume(
        "chat",
        "u",
        now=100,
    )

    worker.consume(
        "chat",
        "u",
        now=100,
    )

    at_109 = worker.check(
        "chat",
        "u",
        now=109,
    )

    eq(
        at_109[
            "remaining_tokens"
        ],
        0,
        "no partial-period refill",
    )

    at_110 = worker.check(
        "chat",
        "u",
        now=110,
    )

    eq(
        at_110[
            "remaining_tokens"
        ],
        1,
        "one complete refill period",
    )

    at_140 = worker.check(
        "chat",
        "u",
        now=140,
    )

    eq(
        at_140[
            "remaining_tokens"
        ],
        3,
        "refill capped at capacity",
    )


def test_weighted_cost():
    worker = manager()

    result = worker.consume(
        "expensive",
        "user",
        now=50,
    )

    eq(
        result[
            "remaining_tokens"
        ],
        7,
        "policy default weighted cost charged",
    )

    custom = worker.consume(
        "expensive",
        "user",
        now=50,
        cost=5,
    )

    eq(
        custom[
            "remaining_tokens"
        ],
        2,
        "per-request custom cost charged",
    )

    denied = worker.consume(
        "expensive",
        "user",
        now=50,
    )

    eq(
        denied[
            "allowed"
        ],
        False,
        "weighted request denied when tokens insufficient",
    )


def test_separate_keys():
    worker = manager()

    for _ in range(
        3
    ):
        worker.consume(
            "chat",
            "user:a",
            now=1,
        )

    denied = worker.consume(
        "chat",
        "user:a",
        now=1,
    )

    other = worker.consume(
        "chat",
        "user:b",
        now=1,
    )

    eq(
        denied[
            "allowed"
        ],
        False,
        "first user exhausted",
    )

    eq(
        other[
            "allowed"
        ],
        True,
        "second user has separate bucket",
    )


def test_disabled_policy():
    worker = RateLimitManager()

    worker.configure_policy(
        "off",
        capacity=1,
        refill_tokens=1,
        refill_seconds=100,
        enabled=False,
    )

    first = worker.consume(
        "off",
        "x",
        now=1,
    )

    second = worker.consume(
        "off",
        "x",
        now=1,
    )

    eq(
        first[
            "allowed"
        ],
        True,
        "disabled policy allows request",
    )

    eq(
        second[
            "allowed"
        ],
        True,
        "disabled policy does not exhaust",
    )

    eq(
        second[
            "remaining_tokens"
        ],
        1,
        "disabled policy leaves tokens unchanged",
    )


def test_policy_replace_resets_buckets():
    worker = manager()

    worker.consume(
        "chat",
        "u",
        now=1,
    )

    worker.consume(
        "chat",
        "u",
        now=1,
    )

    worker.configure_policy(
        "chat",
        capacity=10,
        refill_tokens=2,
        refill_seconds=10,
        cost=1,
        replace=True,
    )

    state = worker.bucket_state(
        "chat",
        "u",
    )

    eq(
        state,
        None,
        "replacing policy invalidates old bucket space",
    )

    fresh = worker.check(
        "chat",
        "u",
        now=2,
    )

    eq(
        fresh[
            "remaining_tokens"
        ],
        10,
        "new policy starts fresh bucket",
    )


def test_reset():
    worker = manager()

    worker.consume(
        "chat",
        "u",
        now=1,
    )

    worker.consume(
        "chat",
        "u",
        now=1,
    )

    reset = worker.reset_key(
        "chat",
        "u",
        now=5,
    )

    eq(
        reset[
            "bucket"
        ][
            "tokens"
        ],
        3,
        "key reset restores capacity",
    )

    cleared = worker.reset_all()

    check(
        cleared[
            "cleared_buckets"
        ] >= 1,
        "reset all clears buckets",
    )

    eq(
        worker.status()[
            "bucket_count"
        ],
        0,
        "bucket count zero after reset all",
    )


def test_time_cannot_move_backwards():
    worker = manager()

    worker.consume(
        "chat",
        "u",
        now=100,
    )

    expect_error(
        ValueError,
        lambda: worker.consume(
            "chat",
            "u",
            now=99,
        ),
        "backward time rejected",
    )


def test_manager_status():
    worker = manager()

    worker.consume(
        "chat",
        "a",
        now=1,
    )

    worker.check(
        "chat",
        "a",
        now=1,
    )

    status = worker.status()

    eq(
        status[
            "policy_count"
        ],
        2,
        "status policy count",
    )

    eq(
        status[
            "bucket_count"
        ],
        1,
        "status bucket count",
    )

    eq(
        status[
            "total_consumes"
        ],
        1,
        "status consume count",
    )

    eq(
        status[
            "total_checks"
        ],
        1,
        "status check count",
    )

    eq(
        status[
            "algorithm"
        ],
        "integer_token_bucket",
        "algorithm reported",
    )


def test_service_flow():
    worker = RateLimitManager()

    service = RateLimitService(
        worker
    )

    configured = service.handle(
        ServiceRequest(
            "s1",
            "rate_limit_service",
            "configure_policy",
            payload={
                "policy_id": "api",
                "capacity": 2,
                "refill_tokens": 1,
                "refill_seconds": 60,
            },
        )
    )

    eq(
        configured.success,
        True,
        "service policy configuration",
    )

    first = service.handle(
        ServiceRequest(
            "s2",
            "rate_limit_service",
            "consume",
            payload={
                "policy_id": "api",
                "key": "client:1",
                "now": 100,
            },
        )
    )

    eq(
        first.data[
            "rate_limit"
        ][
            "allowed"
        ],
        True,
        "service consumes request",
    )

    service.handle(
        ServiceRequest(
            "s3",
            "rate_limit_service",
            "consume",
            payload={
                "policy_id": "api",
                "key": "client:1",
                "now": 100,
            },
        )
    )

    denied = service.handle(
        ServiceRequest(
            "s4",
            "rate_limit_service",
            "consume",
            payload={
                "policy_id": "api",
                "key": "client:1",
                "now": 100,
            },
        )
    )

    eq(
        denied.data[
            "rate_limit"
        ][
            "allowed"
        ],
        False,
        "service reports exhausted bucket",
    )


def test_protocol_round_trip():
    worker = manager()
    service = RateLimitService(
        worker
    )

    codec = ProtocolCodec()

    request = ServiceRequest(
        "protocol-rate",
        "rate_limit_service",
        "consume",
        payload={
            "policy_id": "chat",
            "key": "user:u1",
            "now": 100,
        },
        trace_id="trace-rate",
    )

    request = (
        codec.decode_request(
            codec.encode_request(
                request
            )
        )
    )

    response = service.handle(
        request
    )

    response = (
        codec.decode_response(
            codec.encode_response(
                response
            )
        )
    )

    eq(
        response.success,
        True,
        "rate-limit response survives protocol codec",
    )

    eq(
        response.trace_id,
        "trace-rate",
        "rate-limit trace preserved",
    )

    eq(
        response.data[
            "rate_limit"
        ][
            "remaining_tokens"
        ],
        2,
        "protocol token count",
    )


def test_gateway_anonymous_rate_limit():
    worker = RateLimitManager()

    worker.configure_policy(
        "public",
        capacity=2,
        refill_tokens=1,
        refill_seconds=60,
    )

    current = {
        "now": 100,
    }

    middleware = (
        GatewayRateLimitMiddleware(
            rate_limit_manager=worker,
            now_provider=(
                lambda: current[
                    "now"
                ]
            ),
            default_policy_id="public",
        )
    )

    calls = {
        "count": 0,
    }

    def dispatcher(
        request,
    ):
        calls[
            "count"
        ] += 1

        return (
            ServiceResponse
            .success_response(
                request,
                data={
                    "ok": True,
                },
            )
        )

    gateway = APIGateway(
        middleware=[
            middleware,
        ],
        dispatcher=dispatcher,
    ).register_route(
        GatewayRoute(
            "GET",
            "/public",
            "monitoring_service",
            "health",
        )
    )

    first = gateway.handle(
        GatewayContext(
            "GET",
            "/public",
        )
    )

    second = gateway.handle(
        GatewayContext(
            "GET",
            "/public",
        )
    )

    denied = gateway.handle(
        GatewayContext(
            "GET",
            "/public",
        )
    )

    eq(
        first[
            "status"
        ],
        200,
        "first anonymous gateway request allowed",
    )

    eq(
        second[
            "status"
        ],
        200,
        "second anonymous gateway request allowed",
    )

    eq(
        denied[
            "status"
        ],
        429,
        "third anonymous gateway request rate limited",
    )

    eq(
        calls[
            "count"
        ],
        2,
        "rate-limited request never reaches dispatcher",
    )

    eq(
        denied[
            "error"
        ][
            "code"
        ],
        "RATE_LIMITED",
        "gateway maps rate limit to standard error",
    )


def test_gateway_client_keys_isolated():
    worker = RateLimitManager()

    worker.configure_policy(
        "client-policy",
        capacity=1,
        refill_tokens=1,
        refill_seconds=60,
    )

    middleware = (
        GatewayRateLimitMiddleware(
            rate_limit_manager=worker,
            now_provider=(
                lambda: 100
            ),
            default_policy_id=(
                "client-policy"
            ),
        )
    )

    gateway = APIGateway(
        middleware=[
            middleware,
        ],
        dispatcher=(
            lambda request: (
                ServiceResponse
                .success_response(
                    request
                )
            )
        ),
    ).register_route(
        GatewayRoute(
            "GET",
            "/x",
            "monitoring_service",
            "health",
        )
    )

    a1 = gateway.handle(
        GatewayContext(
            "GET",
            "/x",
            headers={
                "X-Client-ID": "A",
            },
        )
    )

    a2 = gateway.handle(
        GatewayContext(
            "GET",
            "/x",
            headers={
                "X-Client-ID": "A",
            },
        )
    )

    b1 = gateway.handle(
        GatewayContext(
            "GET",
            "/x",
            headers={
                "X-Client-ID": "B",
            },
        )
    )

    eq(
        a1[
            "status"
        ],
        200,
        "client A first request allowed",
    )

    eq(
        a2[
            "status"
        ],
        429,
        "client A exhausted",
    )

    eq(
        b1[
            "status"
        ],
        200,
        "client B independent bucket",
    )


def test_gateway_authenticated_principal_key():
    worker = RateLimitManager()

    worker.configure_policy(
        "user-policy",
        capacity=1,
        refill_tokens=1,
        refill_seconds=60,
    )

    limiter = GatewayRateLimitMiddleware(
        rate_limit_manager=worker,
        now_provider=(
            lambda: 100
        ),
        default_policy_id=(
            "user-policy"
        ),
    )

    class PrincipalMiddleware:
        def before(
            self,
            context,
        ):
            context.authenticated = True
            context.metadata[
                "principal"
            ] = {
                "user_id": "u1",
                "roles": [
                    "user",
                ],
            }

            return None

        def after(
            self,
            context,
            response,
        ):
            return response

    gateway = APIGateway(
        middleware=[
            PrincipalMiddleware(),
            limiter,
            AuthenticationMiddleware(),
        ],
        dispatcher=(
            lambda request: (
                ServiceResponse
                .success_response(
                    request
                )
            )
        ),
    ).register_route(
        GatewayRoute(
            "POST",
            "/v1/chat",
            "rag_service",
            "answer",
            auth_required=True,
        )
    )

    first = gateway.handle(
        GatewayContext(
            "POST",
            "/v1/chat",
        )
    )

    second = gateway.handle(
        GatewayContext(
            "POST",
            "/v1/chat",
        )
    )

    eq(
        first[
            "status"
        ],
        200,
        "authenticated user first request allowed",
    )

    eq(
        first[
            "rate_limit"
        ][
            "key"
        ],
        "user:u1",
        "gateway uses principal user ID as limiter key",
    )

    eq(
        second[
            "status"
        ],
        429,
        "same authenticated principal rate limited",
    )


def test_route_specific_policies():
    worker = RateLimitManager()

    worker.configure_policy(
        "chat",
        capacity=1,
        refill_tokens=1,
        refill_seconds=60,
    )

    worker.configure_policy(
        "health",
        capacity=3,
        refill_tokens=1,
        refill_seconds=60,
    )

    middleware = GatewayRateLimitMiddleware(
        rate_limit_manager=worker,
        now_provider=(
            lambda: 100
        ),
        policy_by_route={
            "POST /v1/chat": (
                "chat"
            ),
            "GET /v1/health": (
                "health"
            ),
        },
    )

    gateway = APIGateway(
        middleware=[
            middleware,
        ],
        dispatcher=(
            lambda request: (
                ServiceResponse
                .success_response(
                    request
                )
            )
        ),
    )

    gateway.register_route(
        GatewayRoute(
            "POST",
            "/v1/chat",
            "rag_service",
            "answer",
        )
    )

    gateway.register_route(
        GatewayRoute(
            "GET",
            "/v1/health",
            "monitoring_service",
            "health",
        )
    )

    gateway.handle(
        GatewayContext(
            "POST",
            "/v1/chat",
        )
    )

    denied_chat = gateway.handle(
        GatewayContext(
            "POST",
            "/v1/chat",
        )
    )

    health = gateway.handle(
        GatewayContext(
            "GET",
            "/v1/health",
        )
    )

    eq(
        denied_chat[
            "status"
        ],
        429,
        "route-specific chat policy enforced",
    )

    eq(
        health[
            "status"
        ],
        200,
        "health route uses independent policy",
    )


def test_errors():
    service = RateLimitService(
        manager()
    )

    missing = service.handle(
        ServiceRequest(
            "m",
            "rate_limit_service",
            "consume",
            payload={
                "policy_id": "missing",
                "key": "u",
                "now": 1,
            },
        )
    )

    eq(
        missing.error.code,
        "NOT_FOUND",
        "missing policy maps to NOT_FOUND",
    )

    invalid = service.handle(
        ServiceRequest(
            "i",
            "rate_limit_service",
            "configure_policy",
            payload={
                "policy_id": "bad",
                "capacity": 0,
                "refill_tokens": 1,
                "refill_seconds": 1,
            },
        )
    )

    eq(
        invalid.error.code,
        "INVALID_REQUEST",
        "invalid policy maps to INVALID_REQUEST",
    )

    wrong = service.handle(
        ServiceRequest(
            "w",
            "rag_service",
            "status",
        )
    )

    eq(
        wrong.error.code,
        "INVALID_REQUEST",
        "wrong service rejected",
    )

    expect_error(
        TypeError,
        lambda: service.handle(
            {}
        ),
        "non-ServiceRequest rejected",
    )


def main():
    test_policy_validation()
    test_bucket_burst_and_denial()
    test_check_does_not_consume()
    test_refill()
    test_weighted_cost()
    test_separate_keys()
    test_disabled_policy()
    test_policy_replace_resets_buckets()
    test_reset()
    test_time_cannot_move_backwards()
    test_manager_status()
    test_service_flow()
    test_protocol_round_trip()
    test_gateway_anonymous_rate_limit()
    test_gateway_client_keys_isolated()
    test_gateway_authenticated_principal_key()
    test_route_specific_policies()
    test_errors()

    print(
        "RATE LIMIT SERVICE TEST SUITE: PASS"
    )
    print(
        "Assertions passed:",
        ASSERTIONS,
    )
    print(
        "Files validated: 5/5"
    )
    print(
        "Integer token-bucket burst/refill: VALIDATED"
    )
    print(
        "Weighted request cost/retry-after: VALIDATED"
    )
    print(
        "Per-user/client bucket isolation: VALIDATED"
    )
    print(
        "Policy replacement/reset semantics: VALIDATED"
    )
    print(
        "API gateway HTTP 429 integration: VALIDATED"
    )
    print(
        "Authenticated principal keying: VALIDATED"
    )
    print(
        "Route-specific policies: VALIDATED"
    )
    print(
        "Protocol service operations: VALIDATED"
    )
    print(
        "Third-party dependencies: 0"
    )


main()
