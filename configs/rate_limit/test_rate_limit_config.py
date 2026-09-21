PARSERS_BASE = "libs/data/parsers/"
PROTOCOL_BASE = "libs/protocol/"
GATEWAY_BASE = "services/api_gateway/"
RATE_LIMIT_BASE = "services/rate_limit_service/"
GATEWAY_CONFIG_BASE = "configs/gateway/"
CONFIG_BASE = "configs/rate_limit/"

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
        ],
    ),
    (
        GATEWAY_BASE,
        [
            "middleware.py",
        ],
    ),
    (
        RATE_LIMIT_BASE,
        [
            "policy.py",
            "bucket.py",
            "manager.py",
            "gateway_adapter.py",
        ],
    ),
    (
        GATEWAY_CONFIG_BASE,
        [
            "route.py",
            "catalog.py",
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
    "config.py",
    "codec.py",
    "validator.py",
    "factory.py",
]:
    path = CONFIG_BASE + filename

    source = open(
        path,
        "r",
        encoding="utf-8",
    ).read()

    if "import " in source:
        raise AssertionError(
            "rate-limit config implementation contains forbidden import: "
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


class Clock:
    def __init__(
        self,
        start=100,
    ):
        self.value = start

    def now(
        self,
    ):
        return self.value

    def advance(
        self,
        seconds,
    ):
        self.value += seconds


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
        ),
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


def gateway_catalog():
    catalog = (
        GatewayConfigCatalog()
    )

    catalog.add(
        GatewayRouteConfig(
            "POST",
            "/v1/chat",
            "rag_service",
            "answer",
            max_payload_bytes=65536,
        )
    )

    catalog.add(
        GatewayRouteConfig(
            "POST",
            "/v1/embed",
            "embedding_service",
            "embed",
            max_payload_bytes=32768,
        )
    )

    return catalog


def test_policy_config():
    policy = RateLimitPolicyConfig(
        "chat",
        capacity=5,
        refill_tokens=2,
        refill_seconds=10,
        cost=1,
    )

    eq(
        policy.capacity,
        5,
        "rate-limit policy capacity",
    )

    eq(
        policy.to_dict()[
            "refill_seconds"
        ],
        10,
        "rate-limit policy serialized",
    )


def test_codec():
    text = (
        '{"policies":['
        '{"policy_id":"chat","capacity":3,'
        '"refill_tokens":1,"refill_seconds":10,"cost":1},'
        '{"policy_id":"embed","capacity":2,'
        '"refill_tokens":2,"refill_seconds":60,"cost":1}'
        '],'
        '"policy_by_route":{'
        '"POST /v1/chat":"chat",'
        '"POST /v1/embed":"embed"'
        '},'
        '"default_policy_id":"chat",'
        '"client_id_header":"X-Client-ID"}'
    )

    config = (
        RateLimitConfigCodec()
        .decode_text(
            text
        )
    )

    eq(
        len(
            config.policies
        ),
        2,
        "codec policy count",
    )

    eq(
        config.client_id_header,
        "x-client-id",
        "client id header normalized",
    )

    eq(
        config.policy_by_route[
            "POST /v1/embed"
        ],
        "embed",
        "codec route mapping",
    )


def test_validator_valid():
    config = RateLimitConfig(
        policies=[
            RateLimitPolicyConfig(
                "chat",
                5,
                1,
                10,
            ),
            RateLimitPolicyConfig(
                "embed",
                2,
                1,
                20,
            ),
        ],
        policy_by_route={
            "POST /v1/chat": "chat",
            "POST /v1/embed": (
                "embed"
            ),
        },
    )

    result = (
        RateLimitConfigValidator()
        .validate(
            config,
            gateway_catalog=(
                gateway_catalog()
            ),
        )
    )

    eq(
        result[
            "valid"
        ],
        True,
        "valid rate-limit config accepted",
    )

    eq(
        result[
            "error_count"
        ],
        0,
        "valid rate-limit config has no errors",
    )


def test_unknown_policy():
    config = RateLimitConfig(
        policies=[
            RateLimitPolicyConfig(
                "chat",
                5,
                1,
                10,
            ),
        ],
        policy_by_route={
            "POST /v1/chat": (
                "missing"
            ),
        },
    )

    result = (
        RateLimitConfigValidator()
        .validate(
            config,
            gateway_catalog=(
                gateway_catalog()
            ),
        )
    )

    eq(
        result[
            "valid"
        ],
        False,
        "unknown route policy invalidates config",
    )

    eq(
        result[
            "errors"
        ][
            0
        ][
            "code"
        ],
        "UNKNOWN_ROUTE_POLICY",
        "unknown route policy error code",
    )


def test_unknown_route():
    config = RateLimitConfig(
        policies=[
            RateLimitPolicyConfig(
                "chat",
                5,
                1,
                10,
            ),
        ],
        policy_by_route={
            "POST /missing": (
                "chat"
            ),
        },
    )

    result = (
        RateLimitConfigValidator()
        .validate(
            config,
            gateway_catalog=(
                gateway_catalog()
            ),
        )
    )

    codes = [
        item[
            "code"
        ]
        for item
        in result[
            "errors"
        ]
    ]

    check(
        "UNKNOWN_GATEWAY_ROUTE"
        in codes,
        "unknown gateway route detected",
    )


def test_factory_manager():
    config = RateLimitConfig(
        policies=[
            RateLimitPolicyConfig(
                "chat",
                capacity=2,
                refill_tokens=1,
                refill_seconds=10,
                cost=1,
            ),
        ],
        default_policy_id="chat",
    )

    manager = (
        RateLimitConfigFactory()
        .build_manager(
            config
        )
    )

    eq(
        manager.status()[
            "policy_count"
        ],
        1,
        "factory configures manager policy",
    )

    first = manager.consume(
        "chat",
        "user:u1",
        now=100,
    )

    second = manager.consume(
        "chat",
        "user:u1",
        now=100,
    )

    third = manager.consume(
        "chat",
        "user:u1",
        now=100,
    )

    eq(
        first[
            "allowed"
        ],
        True,
        "first configured token allowed",
    )

    eq(
        second[
            "allowed"
        ],
        True,
        "second configured token allowed",
    )

    eq(
        third[
            "allowed"
        ],
        False,
        "configured token bucket denies after capacity exhausted",
    )

    refill = manager.consume(
        "chat",
        "user:u1",
        now=110,
    )

    eq(
        refill[
            "allowed"
        ],
        True,
        "configured token bucket refills",
    )


def test_gateway_middleware():
    clock = Clock(
        200
    )

    config = RateLimitConfig(
        policies=[
            RateLimitPolicyConfig(
                "chat",
                capacity=1,
                refill_tokens=1,
                refill_seconds=10,
            ),
        ],
        policy_by_route={
            "POST /v1/chat": (
                "chat"
            ),
        },
        client_id_header=(
            "x-client-id"
        ),
    )

    factory = (
        RateLimitConfigFactory()
    )

    manager = (
        factory.build_manager(
            config
        )
    )

    middleware = (
        factory
        .build_gateway_middleware(
            config,
            manager,
            clock.now,
        )
    )

    context = GatewayContext(
        "POST",
        "/v1/chat",
        headers={
            "X-Client-ID": (
                "client-a"
            ),
        },
    )

    first = middleware.before(
        context
    )

    eq(
        first,
        None,
        "first gateway request passes rate-limit middleware",
    )

    eq(
        context.metadata[
            "rate_limit"
        ][
            "key"
        ],
        "client:client-a",
        "middleware resolves configured client id header",
    )

    second_context = GatewayContext(
        "POST",
        "/v1/chat",
        headers={
            "x-client-id": (
                "client-a"
            ),
        },
    )

    second = middleware.before(
        second_context
    )

    check(
        isinstance(
            second,
            ProtocolError,
        ),
        "second gateway request receives protocol error",
    )

    eq(
        second.code,
        "RATE_LIMITED",
        "gateway middleware returns RATE_LIMITED",
    )

    clock.advance(
        10
    )

    third_context = GatewayContext(
        "POST",
        "/v1/chat",
        headers={
            "x-client-id": (
                "client-a"
            ),
        },
    )

    third = middleware.before(
        third_context
    )

    eq(
        third,
        None,
        "gateway middleware allows request after refill",
    )


def test_principal_precedence():
    config = RateLimitConfig(
        policies=[
            RateLimitPolicyConfig(
                "default",
                5,
                1,
                10,
            ),
        ],
        default_policy_id=(
            "default"
        ),
    )

    factory = (
        RateLimitConfigFactory()
    )

    manager = (
        factory.build_manager(
            config
        )
    )

    middleware = (
        factory
        .build_gateway_middleware(
            config,
            manager,
            lambda: 1,
        )
    )

    context = GatewayContext(
        "POST",
        "/anything",
        headers={
            "x-client-id": "client-a",
        },
    )

    context.metadata[
        "principal"
    ] = {
        "user_id": "user-7",
    }

    middleware.before(
        context
    )

    eq(
        context.metadata[
            "rate_limit"
        ][
            "key"
        ],
        "user:user-7",
        "authenticated principal outranks client header",
    )


def test_duplicate_policy_rejected():
    expect_error(
        ValueError,
        lambda: RateLimitConfig(
            policies=[
                RateLimitPolicyConfig(
                    "same",
                    1,
                    1,
                    1,
                ),
                RateLimitPolicyConfig(
                    "same",
                    2,
                    1,
                    1,
                ),
            ],
        ),
        "duplicate policy rejected",
    )


def main():
    test_policy_config()
    test_codec()
    test_validator_valid()
    test_unknown_policy()
    test_unknown_route()
    test_factory_manager()
    test_gateway_middleware()
    test_principal_precedence()
    test_duplicate_policy_rejected()

    print(
        "RATE LIMIT CONFIG TEST SUITE: PASS"
    )
    print(
        "Assertions passed:",
        ASSERTIONS,
    )
    print(
        "Files validated: 5/5"
    )
    print(
        "Typed token-bucket policies: VALIDATED"
    )
    print(
        "Handwritten JSON decoding: VALIDATED"
    )
    print(
        "Gateway route/policy cross-validation: VALIDATED"
    )
    print(
        "RateLimitManager generation: VALIDATED"
    )
    print(
        "Token consumption/refill semantics: VALIDATED"
    )
    print(
        "Gateway rate-limit middleware generation: VALIDATED"
    )
    print(
        "Principal/client key resolution: VALIDATED"
    )
    print(
        "Third-party dependencies: 0"
    )


main()
