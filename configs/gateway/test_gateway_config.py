PARSERS_BASE = "libs/data/parsers/"
GATEWAY_BASE = "services/api_gateway/"
SERVICE_CONFIG_BASE = "configs/services/"
CONFIG_BASE = "configs/gateway/"

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
        GATEWAY_BASE,
        [
            "route.py",
        ],
    ),
    (
        SERVICE_CONFIG_BASE,
        [
            "instance.py",
            "definition.py",
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
    "route.py",
    "catalog.py",
    "codec.py",
    "validator.py",
    "factory.py",
]:
    path = (
        CONFIG_BASE
        + filename
    )

    source = open(
        path,
        "r",
        encoding="utf-8",
    ).read()

    if "import " in source:
        raise AssertionError(
            "gateway config implementation contains forbidden import: "
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


def service_catalog():
    catalog = (
        ServiceConfigCatalog()
    )

    catalog.add(
        ServiceDefinition(
            "rag_service",
            [
                ServiceInstanceConfig(
                    "rag-1"
                ),
            ],
        )
    )

    catalog.add(
        ServiceDefinition(
            "embedding_service",
            [
                ServiceInstanceConfig(
                    "embed-1"
                ),
            ],
        )
    )

    return catalog


def test_route_config():
    route = GatewayRouteConfig(
        "post",
        "/v1/chat",
        "rag_service",
        "answer",
        auth_required=True,
        max_payload_bytes=1024,
        tags=[
            "rag",
            "chat",
            "rag",
        ],
    )

    eq(
        route.method,
        "POST",
        "route method normalized",
    )

    eq(
        route.tags,
        [
            "rag",
            "chat",
        ],
        "route tags deduplicated",
    )

    eq(
        route.key(),
        "POST /v1/chat",
        "route key",
    )


def test_catalog():
    catalog = (
        GatewayConfigCatalog()
    )

    catalog.add(
        GatewayRouteConfig(
            "GET",
            "/health",
            "runtime_control",
            "status",
        )
    )

    catalog.add(
        GatewayRouteConfig(
            "POST",
            "/disabled",
            "rag_service",
            "answer",
            enabled=False,
        )
    )

    eq(
        catalog.count(),
        2,
        "gateway catalog total routes",
    )

    eq(
        catalog.count(
            enabled_only=True
        ),
        1,
        "gateway catalog enabled routes",
    )

    expect_error(
        ValueError,
        lambda: catalog.add(
            GatewayRouteConfig(
                "GET",
                "/health",
                "runtime_control",
                "status",
            )
        ),
        "duplicate method/path rejected",
    )


def test_codec():
    text = (
        '{"routes":['
        '{"method":"POST","path":"/v1/chat",'
        '"service":"rag_service","operation":"answer",'
        '"auth_required":false,"max_payload_bytes":65536,'
        '"tags":["chat","rag"]},'
        '{"method":"POST","path":"/v1/embed",'
        '"service":"embedding_service","operation":"embed",'
        '"auth_required":true,"max_payload_bytes":32768,'
        '"enabled":false}'
        ']}'
    )

    catalog = (
        GatewayConfigCodec()
        .decode_text(
            text
        )
    )

    eq(
        catalog.count(),
        2,
        "codec route count",
    )

    eq(
        catalog.get(
            "POST",
            "/v1/chat",
        ).auth_required,
        False,
        "codec maps auth requirement",
    )

    eq(
        catalog.get(
            "POST",
            "/v1/embed",
        ).enabled,
        False,
        "codec maps enabled flag",
    )


def test_validator_valid():
    catalog = (
        GatewayConfigCatalog()
    )

    catalog.add(
        GatewayRouteConfig(
            "POST",
            "/v1/chat",
            "rag_service",
            "answer",
            max_payload_bytes=(
                65536
            ),
        )
    )

    catalog.add(
        GatewayRouteConfig(
            "GET",
            "/admin/status",
            "runtime_control",
            "status",
            max_payload_bytes=(
                1024
            ),
        )
    )

    result = (
        GatewayConfigValidator()
        .validate(
            catalog,
            service_catalog=(
                service_catalog()
            ),
        )
    )

    eq(
        result[
            "valid"
        ],
        True,
        "valid gateway configuration accepted",
    )

    eq(
        result[
            "error_count"
        ],
        0,
        "valid gateway has no errors",
    )


def test_unknown_service_rejected():
    catalog = (
        GatewayConfigCatalog()
    )

    catalog.add(
        GatewayRouteConfig(
            "POST",
            "/v1/missing",
            "missing_service",
            "run",
            max_payload_bytes=1024,
        )
    )

    result = (
        GatewayConfigValidator()
        .validate(
            catalog,
            service_catalog=(
                service_catalog()
            ),
        )
    )

    eq(
        result[
            "valid"
        ],
        False,
        "unknown service invalidates gateway config",
    )

    eq(
        result[
            "errors"
        ][
            0
        ][
            "code"
        ],
        "UNKNOWN_TARGET_SERVICE",
        "unknown target service error code",
    )


def test_method_and_warning_rules():
    catalog = (
        GatewayConfigCatalog()
    )

    catalog.add(
        GatewayRouteConfig(
            "TRACE",
            "/v1/debug/",
            "rag_service",
            "debug",
        )
    )

    result = (
        GatewayConfigValidator()
        .validate(
            catalog,
            service_catalog=(
                service_catalog()
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

    warnings = [
        item[
            "code"
        ]
        for item
        in result[
            "warnings"
        ]
    ]

    check(
        "UNSUPPORTED_METHOD"
        in codes,
        "unsupported method detected",
    )

    check(
        "TRAILING_SLASH"
        in warnings,
        "trailing slash warning emitted",
    )


def test_payload_warning():
    catalog = (
        GatewayConfigCatalog()
    )

    catalog.add(
        GatewayRouteConfig(
            "POST",
            "/v1/chat",
            "rag_service",
            "answer",
        )
    )

    result = (
        GatewayConfigValidator()
        .validate(
            catalog,
            service_catalog=(
                service_catalog()
            ),
        )
    )

    codes = [
        item[
            "code"
        ]
        for item
        in result[
            "warnings"
        ]
    ]

    check(
        "NO_PAYLOAD_LIMIT"
        in codes,
        "body route without payload limit warned",
    )


def test_factory():
    catalog = (
        GatewayConfigCatalog()
    )

    catalog.add(
        GatewayRouteConfig(
            "POST",
            "/v1/chat",
            "rag_service",
            "answer",
            auth_required=False,
            max_payload_bytes=65536,
            tags=[
                "chat",
                "rag",
            ],
        )
    )

    catalog.add(
        GatewayRouteConfig(
            "POST",
            "/disabled",
            "rag_service",
            "answer",
            enabled=False,
            max_payload_bytes=1024,
        )
    )

    routes = (
        GatewayRouteConfigFactory()
        .build(
            catalog,
            service_catalog=(
                service_catalog()
            ),
        )
    )

    eq(
        len(
            routes
        ),
        1,
        "factory excludes disabled routes",
    )

    route = routes[
        0
    ]

    check(
        isinstance(
            route,
            GatewayRoute,
        ),
        "factory returns runtime GatewayRoute",
    )

    eq(
        route.service,
        "rag_service",
        "factory preserves service target",
    )

    eq(
        route.tags,
        [
            "chat",
            "rag",
        ],
        "factory preserves tags",
    )


def test_require_valid():
    catalog = (
        GatewayConfigCatalog()
    )

    catalog.add(
        GatewayRouteConfig(
            "POST",
            "/bad",
            "missing",
            "run",
            max_payload_bytes=1,
        )
    )

    expect_error(
        ValueError,
        lambda: (
            GatewayConfigValidator()
            .require_valid(
                catalog,
                service_catalog=(
                    service_catalog()
                ),
            )
        ),
        "require_valid rejects broken gateway config",
    )


def main():
    test_route_config()
    test_catalog()
    test_codec()
    test_validator_valid()
    test_unknown_service_rejected()
    test_method_and_warning_rules()
    test_payload_warning()
    test_factory()
    test_require_valid()

    print(
        "GATEWAY CONFIG TEST SUITE: PASS"
    )
    print(
        "Assertions passed:",
        ASSERTIONS,
    )
    print(
        "Files validated: 5/5"
    )
    print(
        "Typed gateway route configuration: VALIDATED"
    )
    print(
        "Handwritten JSON decoding: VALIDATED"
    )
    print(
        "Duplicate route prevention: VALIDATED"
    )
    print(
        "Cross-validation against service catalog: VALIDATED"
    )
    print(
        "Payload/method/path validation rules: VALIDATED"
    )
    print(
        "GatewayRoute runtime generation: VALIDATED"
    )
    print(
        "Disabled-route exclusion: VALIDATED"
    )
    print(
        "Third-party dependencies: 0"
    )


main()
