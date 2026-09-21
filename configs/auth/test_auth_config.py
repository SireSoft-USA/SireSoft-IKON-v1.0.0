PARSERS_BASE = "libs/data/parsers/"
PROTOCOL_BASE = "libs/protocol/"
AUTH_BASE = "services/auth_service/"
GATEWAY_CONFIG_BASE = "configs/gateway/"
CONFIG_BASE = "configs/auth/"

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
        AUTH_BASE,
        [
            "user.py",
            "policy.py",
            "crypto.py",
            "token.py",
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
    "role.py",
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
            "auth config implementation contains forbidden import: "
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
            auth_required=True,
            max_payload_bytes=65536,
        )
    )

    catalog.add(
        GatewayRouteConfig(
            "GET",
            "/v1/health",
            "runtime_control",
            "status",
            auth_required=False,
            max_payload_bytes=1024,
        )
    )

    return catalog


def test_role_config():
    role = AuthRoleConfig(
        "developer",
        [
            "chat:use",
            "chat:use",
            "retrieval:search",
        ],
    )

    eq(
        role.permissions,
        [
            "chat:use",
            "retrieval:search",
        ],
        "role permissions deduplicated",
    )


def test_codec():
    text = (
        '{"roles":{'
        '"user":["chat:use"],'
        '"developer":["chat:use","retrieval:search"]'
        '},'
        '"password_iterations":32,'
        '"min_password_length":8,'
        '"max_failed_attempts":4,'
        '"default_session_ttl_seconds":900,'
        '"permission_by_route":{'
        '"POST /v1/chat":"chat:use"'
        '}}'
    )

    config = (
        AuthConfigCodec()
        .decode_text(
            text
        )
    )

    eq(
        config.password_iterations,
        32,
        "codec maps password iterations",
    )

    eq(
        config.default_session_ttl_seconds,
        900,
        "codec maps session TTL",
    )

    eq(
        config.permission_by_route[
            "POST /v1/chat"
        ],
        "chat:use",
        "codec maps route permission",
    )


def test_secret_not_serialized():
    config = AuthConfig(
        roles=[
            AuthRoleConfig(
                "user",
                [
                    "chat:use",
                ],
            ),
        ],
    )

    public = config.to_dict()

    check(
        "server_secret"
        not in public,
        "auth config never serializes server secret",
    )


def test_validator():
    config = AuthConfig(
        roles=[
            AuthRoleConfig(
                "user",
                [
                    "chat:use",
                ],
            ),
        ],
        permission_by_route={
            "POST /v1/chat": (
                "chat:use"
            ),
        },
    )

    result = (
        AuthConfigValidator()
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
        "known protected route validation succeeds",
    )

    eq(
        result[
            "error_count"
        ],
        0,
        "valid auth config has no errors",
    )


def test_unknown_route_validation():
    config = AuthConfig(
        roles=[
            AuthRoleConfig(
                "user",
                [
                    "chat:use",
                ],
            ),
        ],
        permission_by_route={
            "POST /missing": (
                "chat:use"
            ),
        },
    )

    result = (
        AuthConfigValidator()
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
        "unknown protected route invalidates auth config",
    )

    eq(
        result[
            "errors"
        ][
            0
        ][
            "code"
        ],
        "UNKNOWN_GATEWAY_ROUTE",
        "unknown gateway route error code",
    )


def test_public_route_warning():
    config = AuthConfig(
        roles=[
            AuthRoleConfig(
                "operator",
                [
                    "monitoring:read",
                ],
            ),
        ],
        permission_by_route={
            "GET /v1/health": (
                "monitoring:read"
            ),
        },
    )

    result = (
        AuthConfigValidator()
        .validate(
            config,
            gateway_catalog=(
                gateway_catalog()
            ),
        )
    )

    warning_codes = [
        item[
            "code"
        ]
        for item
        in result[
            "warnings"
        ]
    ]

    check(
        "PERMISSION_ON_PUBLIC_ROUTE"
        in warning_codes,
        "permission on public route warned",
    )


def test_factory_policy_and_manager():
    config = AuthConfig(
        roles=[
            AuthRoleConfig(
                "user",
                [
                    "chat:use",
                ],
            ),
            AuthRoleConfig(
                "admin",
                [
                    "*",
                ],
            ),
        ],
        password_iterations=16,
        min_password_length=8,
        max_failed_attempts=3,
        default_session_ttl_seconds=120,
        permission_by_route={
            "POST /v1/chat": (
                "chat:use"
            ),
        },
    )

    factory = (
        AuthConfigFactory()
    )

    policy = (
        factory
        .build_permission_policy(
            config
        )
    )

    eq(
        policy.allowed(
            [
                "user",
            ],
            "chat:use",
        ),
        True,
        "factory policy allows configured permission",
    )

    manager = (
        factory
        .build_manager(
            config,
            server_secret=(
                "0123456789abcdef-strong"
            ),
        )
    )

    manager.create_user(
        user_id="u1",
        username="alice",
        password="password123",
        roles=[
            "user",
        ],
    )

    session = manager.authenticate(
        "alice",
        "password123",
        now=100,
        ttl_seconds=(
            config
            .default_session_ttl_seconds
        ),
    )

    check(
        isinstance(
            session[
                "token"
            ],
            str,
        ),
        "configured auth manager issues token",
    )

    principal = manager.verify_token(
        session[
            "token"
        ],
        now=101,
    )

    eq(
        principal[
            "user_id"
        ],
        "u1",
        "configured auth manager verifies token",
    )


def test_gateway_middleware_factory():
    config = AuthConfig(
        roles=[
            AuthRoleConfig(
                "user",
                [
                    "chat:use",
                ],
            ),
        ],
        permission_by_route={
            "POST /v1/chat": (
                "chat:use"
            ),
        },
    )

    factory = AuthConfigFactory()

    manager = factory.build_manager(
        config,
        "0123456789abcdef-strong",
    )

    middleware = (
        factory
        .build_gateway_middleware(
            config,
            manager,
            lambda: 100,
        )
    )

    check(
        isinstance(
            middleware,
            GatewayTokenAuthenticationMiddleware,
        ),
        "factory creates gateway auth middleware",
    )

    eq(
        middleware.permission_by_route[
            "POST /v1/chat"
        ],
        "chat:use",
        "gateway middleware receives permission map",
    )


def test_duplicate_role_rejected():
    expect_error(
        ValueError,
        lambda: AuthConfig(
            roles=[
                AuthRoleConfig(
                    "user",
                    [
                        "chat:use",
                    ],
                ),
                AuthRoleConfig(
                    "user",
                    [
                        "other",
                    ],
                ),
            ],
        ),
        "duplicate auth role rejected",
    )


def main():
    test_role_config()
    test_codec()
    test_secret_not_serialized()
    test_validator()
    test_unknown_route_validation()
    test_public_route_warning()
    test_factory_policy_and_manager()
    test_gateway_middleware_factory()
    test_duplicate_role_rejected()

    print(
        "AUTH CONFIG TEST SUITE: PASS"
    )
    print(
        "Assertions passed:",
        ASSERTIONS,
    )
    print(
        "Files validated: 5/5"
    )
    print(
        "Typed roles/permissions: VALIDATED"
    )
    print(
        "Secret/config separation: VALIDATED"
    )
    print(
        "Gateway route permission validation: VALIDATED"
    )
    print(
        "PermissionPolicy generation: VALIDATED"
    )
    print(
        "AuthManager generation: VALIDATED"
    )
    print(
        "Token issue/verification integration: VALIDATED"
    )
    print(
        "Gateway auth middleware generation: VALIDATED"
    )
    print(
        "Third-party dependencies: 0"
    )


main()
