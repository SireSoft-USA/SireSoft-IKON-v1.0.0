SERIAL_BASE = "libs/core/serialization/"
PROTOCOL_BASE = "libs/protocol/"
GATEWAY_BASE = "services/api_gateway/"
SERVICE_BASE = "services/auth_service/"

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
    "crypto.py",
    "user.py",
    "policy.py",
    "token.py",
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
            "auth_service implementation contains forbidden import: "
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


def manager(
    iterations=256,
):
    return AuthManager(
        server_secret=(
            "unit-test-server-secret-"
            "with-more-than-16-chars"
        ),
        password_iterations=(
            iterations
        ),
        min_password_length=8,
        max_failed_attempts=3,
    )


def test_sha256_vectors():
    crypto = AuthCrypto()

    eq(
        crypto.to_hex(
            crypto.sha256(
                b""
            )
        ),
        (
            "e3b0c44298fc1c149afbf4c8996fb924"
            "27ae41e4649b934ca495991b7852b855"
        ),
        "SHA-256 empty vector",
    )

    eq(
        crypto.to_hex(
            crypto.sha256(
                b"abc"
            )
        ),
        (
            "ba7816bf8f01cfea414140de5dae2223"
            "b00361a396177a9cb410ff61f20015ad"
        ),
        "SHA-256 abc vector",
    )


def test_hmac_vector():
    crypto = AuthCrypto()

    key = bytes(
        [0x0B] * 20
    )

    digest = crypto.to_hex(
        crypto.hmac_sha256(
            key,
            b"Hi There",
        )
    )

    eq(
        digest,
        (
            "b0344c61d8db38535ca8afceaf0bf12b"
            "881dc200c9833da726e9376c2e32cff7"
        ),
        "HMAC-SHA256 RFC vector",
    )


def test_pbkdf2_vector():
    crypto = AuthCrypto()

    digest = crypto.to_hex(
        crypto.pbkdf2_hmac_sha256(
            b"password",
            b"salt",
            1,
            32,
        )
    )

    eq(
        digest,
        (
            "120fb6cffcf8b32c43e7225256c4f837"
            "a86548c92ccc35480805987cb70be17b"
        ),
        "PBKDF2-HMAC-SHA256 iteration-1 vector",
    )


def test_user_creation_no_plaintext():
    worker = manager()

    user = worker.create_user(
        "u1",
        "Anamta",
        "StrongPass123",
        roles=[
            "developer",
        ],
        metadata={
            "team": "engineering",
        },
    )

    eq(
        user.username,
        "Anamta",
        "username preserved",
    )

    eq(
        user.roles,
        [
            "developer",
        ],
        "role preserved",
    )

    check(
        user.password_record.digest_hex
        != "StrongPass123",
        "plaintext password not stored",
    )

    public = user.public_dict()

    check(
        "password"
        not in public,
        "public user omits password",
    )

    check(
        "digest_hex"
        not in public,
        "public user omits password digest",
    )


def test_duplicate_identity_validation():
    worker = manager()

    worker.create_user(
        "u1",
        "UserOne",
        "Password123",
    )

    expect_error(
        ValueError,
        lambda: worker.create_user(
            "u1",
            "Other",
            "Password123",
        ),
        "duplicate user ID rejected",
    )

    expect_error(
        ValueError,
        lambda: worker.create_user(
            "u2",
            "userone",
            "Password123",
        ),
        "case-insensitive duplicate username rejected",
    )


def test_authenticate_verify():
    worker = manager()

    worker.create_user(
        "u1",
        "developer1",
        "Password123",
        roles=[
            "developer",
        ],
    )

    login = worker.authenticate(
        "developer1",
        "Password123",
        now=1000,
        ttl_seconds=100,
    )

    check(
        login[
            "token"
        ].startswith(
            "sllm1."
        ),
        "token format prefix",
    )

    eq(
        login[
            "principal"
        ][
            "user_id"
        ],
        "u1",
        "principal user",
    )

    principal = worker.verify_token(
        login[
            "token"
        ],
        now=1050,
    )

    eq(
        principal[
            "roles"
        ],
        [
            "developer",
        ],
        "verified token roles",
    )

    check(
        "retrieval:search"
        in principal[
            "permissions"
        ],
        "principal permission expansion",
    )


def test_bad_password_and_lock():
    worker = manager()

    worker.create_user(
        "u1",
        "user1",
        "Password123",
    )

    for attempt in range(
        3
    ):
        expect_error(
            PermissionError,
            lambda: worker.authenticate(
                "user1",
                "WrongPass123",
                now=1000,
            ),
            "bad password rejected",
        )

    eq(
        worker.get_user(
            "u1"
        ).status,
        "locked",
        "failed attempts lock user",
    )

    expect_error(
        PermissionError,
        lambda: worker.authenticate(
            "user1",
            "Password123",
            now=1001,
        ),
        "locked account cannot login",
    )

    worker.enable_user(
        "u1"
    )

    login = worker.authenticate(
        "user1",
        "Password123",
        now=1002,
    )

    check(
        login[
            "token"
        ] != "",
        "enabled user authenticates again",
    )


def test_expiry():
    worker = manager()

    worker.create_user(
        "u1",
        "user1",
        "Password123",
    )

    login = worker.authenticate(
        "user1",
        "Password123",
        now=100,
        ttl_seconds=10,
    )

    expect_error(
        PermissionError,
        lambda: worker.verify_token(
            login[
                "token"
            ],
            now=110,
        ),
        "token expires exactly at expires_at",
    )


def test_token_tamper():
    worker = manager()

    worker.create_user(
        "u1",
        "user1",
        "Password123",
    )

    token = worker.authenticate(
        "user1",
        "Password123",
        now=100,
    )[
        "token"
    ]

    replacement = (
        "0"
        if token[
            -1
        ] != "0"
        else "1"
    )

    tampered = (
        token[
            :-1
        ]
        + replacement
    )

    expect_error(
        ValueError,
        lambda: worker.verify_token(
            tampered,
            now=101,
        ),
        "tampered token signature rejected",
    )


def test_revoke():
    worker = manager()

    worker.create_user(
        "u1",
        "user1",
        "Password123",
    )

    login = worker.authenticate(
        "user1",
        "Password123",
        now=100,
    )

    session = worker.revoke_token(
        login[
            "token"
        ],
        now=101,
    )

    eq(
        session[
            "revoked"
        ],
        True,
        "token session revoked",
    )

    expect_error(
        PermissionError,
        lambda: worker.verify_token(
            login[
                "token"
            ],
            now=102,
        ),
        "revoked token rejected",
    )


def test_password_change_revokes_sessions():
    worker = manager()

    worker.create_user(
        "u1",
        "user1",
        "Password123",
    )

    login = worker.authenticate(
        "user1",
        "Password123",
        now=100,
    )

    user = worker.change_password(
        "u1",
        "Password123",
        "NewPassword456",
    )

    eq(
        user[
            "credential_version"
        ],
        2,
        "credential version increments",
    )

    expect_error(
        PermissionError,
        lambda: worker.verify_token(
            login[
                "token"
            ],
            now=101,
        ),
        "old token invalid after password change",
    )

    expect_error(
        PermissionError,
        lambda: worker.authenticate(
            "user1",
            "Password123",
            now=102,
        ),
        "old password rejected",
    )

    new_login = worker.authenticate(
        "user1",
        "NewPassword456",
        now=103,
    )

    check(
        new_login[
            "token"
        ] != "",
        "new password authenticates",
    )


def test_disable_user():
    worker = manager()

    worker.create_user(
        "u1",
        "user1",
        "Password123",
    )

    login = worker.authenticate(
        "user1",
        "Password123",
        now=100,
    )

    worker.disable_user(
        "u1"
    )

    expect_error(
        PermissionError,
        lambda: worker.verify_token(
            login[
                "token"
            ],
            now=101,
        ),
        "disabled user token rejected",
    )

    expect_error(
        PermissionError,
        lambda: worker.authenticate(
            "user1",
            "Password123",
            now=102,
        ),
        "disabled user cannot login",
    )


def test_permissions_and_roles():
    worker = manager()

    worker.create_user(
        "u1",
        "dev",
        "Password123",
        roles=[
            "developer",
        ],
    )

    login = worker.authenticate(
        "dev",
        "Password123",
        now=100,
    )

    allowed = worker.authorize(
        login[
            "principal"
        ],
        "retrieval:search",
    )

    eq(
        allowed[
            "allowed"
        ],
        True,
        "developer retrieval permission",
    )

    denied = worker.authorize(
        login[
            "principal"
        ],
        "training:manage",
    )

    eq(
        denied[
            "allowed"
        ],
        False,
        "developer training permission denied",
    )

    worker.grant_role(
        "u1",
        "operator",
    )

    expect_error(
        PermissionError,
        lambda: worker.verify_token(
            login[
                "token"
            ],
            now=101,
        ),
        "role change revokes existing sessions",
    )

    refreshed = worker.authenticate(
        "dev",
        "Password123",
        now=102,
    )

    eq(
        worker.authorize(
            refreshed[
                "principal"
            ],
            "training:manage",
        )[
            "allowed"
        ],
        True,
        "operator role grants training permission",
    )


def test_admin_wildcard():
    worker = manager()

    worker.create_user(
        "admin",
        "admin",
        "AdminPassword123",
        roles=[
            "admin",
        ],
    )

    login = worker.authenticate(
        "admin",
        "AdminPassword123",
        now=100,
    )

    eq(
        worker.authorize(
            login[
                "principal"
            ],
            "anything:anywhere",
        )[
            "allowed"
        ],
        True,
        "admin wildcard permission",
    )


def test_status():
    worker = manager()

    worker.create_user(
        "u1",
        "user1",
        "Password123",
    )

    worker.create_user(
        "u2",
        "user2",
        "Password123",
    )

    worker.disable_user(
        "u2"
    )

    worker.authenticate(
        "user1",
        "Password123",
        now=100,
    )

    status = worker.status()

    eq(
        status[
            "users"
        ],
        2,
        "status user count",
    )

    eq(
        status[
            "active_users"
        ],
        1,
        "status active users",
    )

    eq(
        status[
            "disabled_users"
        ],
        1,
        "status disabled users",
    )

    eq(
        status[
            "password_kdf"
        ],
        "PBKDF2-HMAC-SHA256",
        "status reports password KDF",
    )

    eq(
        status[
            "crypto_implementation"
        ],
        "pure_python_educational",
        "status accurately labels crypto implementation",
    )


def test_service_flow():
    worker = manager()

    service = AuthService(
        worker
    )

    created = service.handle(
        ServiceRequest(
            "a1",
            "auth_service",
            "create_user",
            payload={
                "user_id": "u1",
                "username": "developer",
                "password": "Password123",
                "roles": [
                    "developer",
                ],
            },
        )
    )

    eq(
        created.success,
        True,
        "service user creation",
    )

    check(
        "password"
        not in created.data[
            "user"
        ],
        "service user response has no password",
    )

    login = service.handle(
        ServiceRequest(
            "a2",
            "auth_service",
            "authenticate",
            payload={
                "identifier": "developer",
                "password": "Password123",
                "now": 1000,
                "ttl_seconds": 100,
            },
        )
    )

    eq(
        login.success,
        True,
        "service authentication",
    )

    verified = service.handle(
        ServiceRequest(
            "a3",
            "auth_service",
            "verify_token",
            payload={
                "token": login.data[
                    "token"
                ],
                "now": 1010,
            },
        )
    )

    eq(
        verified.success,
        True,
        "service token verification",
    )

    authz = service.handle(
        ServiceRequest(
            "a4",
            "auth_service",
            "authorize",
            payload={
                "principal": (
                    verified.data[
                        "principal"
                    ]
                ),
                "permission": (
                    "retrieval:search"
                ),
            },
        )
    )

    eq(
        authz.data[
            "authorization"
        ][
            "allowed"
        ],
        True,
        "service authorization",
    )


def test_service_errors():
    worker = manager()
    service = AuthService(
        worker
    )

    worker.create_user(
        "u1",
        "user1",
        "Password123",
    )

    bad = service.handle(
        ServiceRequest(
            "e1",
            "auth_service",
            "authenticate",
            payload={
                "identifier": "user1",
                "password": "wrong-password",
                "now": 1,
            },
        )
    )

    eq(
        bad.error.code,
        "UNAUTHENTICATED",
        "bad credentials map to UNAUTHENTICATED",
    )

    missing = service.handle(
        ServiceRequest(
            "e2",
            "auth_service",
            "get_user",
            payload={
                "user_id": "missing",
            },
        )
    )

    eq(
        missing.error.code,
        "NOT_FOUND",
        "missing user maps to NOT_FOUND",
    )

    wrong = service.handle(
        ServiceRequest(
            "e3",
            "rag_service",
            "status",
        )
    )

    eq(
        wrong.error.code,
        "INVALID_REQUEST",
        "wrong service rejected",
    )


def test_protocol_round_trip():
    worker = manager()
    service = AuthService(
        worker
    )

    codec = ProtocolCodec()

    create_request = ServiceRequest(
        "protocol-create",
        "auth_service",
        "create_user",
        payload={
            "user_id": "u1",
            "username": "user1",
            "password": "Password123",
        },
        trace_id="trace-auth",
    )

    create_request = (
        codec.decode_request(
            codec.encode_request(
                create_request
            )
        )
    )

    create_response = (
        service.handle(
            create_request
        )
    )

    create_response = (
        codec.decode_response(
            codec.encode_response(
                create_response
            )
        )
    )

    eq(
        create_response.success,
        True,
        "auth user creation survives protocol codec",
    )

    eq(
        create_response.trace_id,
        "trace-auth",
        "auth trace preserved",
    )

    login = service.handle(
        ServiceRequest(
            "protocol-login",
            "auth_service",
            "authenticate",
            payload={
                "identifier": "user1",
                "password": "Password123",
                "now": 100,
            },
        )
    )

    encoded = codec.encode_response(
        login
    )

    decoded = codec.decode_response(
        encoded
    )

    eq(
        decoded.data[
            "principal"
        ][
            "user_id"
        ],
        "u1",
        "auth principal survives binary protocol",
    )


def test_gateway_authentication_integration():
    worker = manager()

    worker.create_user(
        "u1",
        "developer",
        "Password123",
        roles=[
            "developer",
        ],
    )

    login = worker.authenticate(
        "developer",
        "Password123",
        now=100,
        ttl_seconds=100,
    )

    captured = {
        "request": None,
    }

    def dispatcher(
        request,
    ):
        captured[
            "request"
        ] = request

        return (
            ServiceResponse
            .success_response(
                request,
                data={
                    "ok": True,
                },
            )
        )

    auth_middleware = (
        GatewayTokenAuthenticationMiddleware(
            auth_manager=worker,
            now_provider=(
                lambda: 120
            ),
            permission_by_route={
                (
                    "POST "
                    "/v1/retrieve"
                ): (
                    "retrieval:search"
                ),
            },
        )
    )

    gateway = APIGateway(
        middleware=[
            auth_middleware,
            AuthenticationMiddleware(),
            PayloadLimitMiddleware(),
        ],
        dispatcher=dispatcher,
    ).register_route(
        GatewayRoute(
            "POST",
            "/v1/retrieve",
            "retrieval_service",
            "search",
            auth_required=True,
        )
    )

    response = gateway.handle(
        GatewayContext(
            "POST",
            "/v1/retrieve",
            payload={
                "query": "software",
            },
            headers={
                "Authorization": (
                    "Bearer "
                    + login[
                        "token"
                    ]
                ),
            },
            authenticated=False,
        )
    )

    eq(
        response[
            "status"
        ],
        200,
        "Bearer token authenticates protected API gateway route",
    )

    eq(
        captured[
            "request"
        ].service,
        "retrieval_service",
        "authenticated route reaches dispatcher",
    )


def test_gateway_missing_token_blocked():
    worker = manager()

    gateway = APIGateway(
        middleware=[
            GatewayTokenAuthenticationMiddleware(
                auth_manager=worker,
                now_provider=(
                    lambda: 100
                ),
            ),
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
        )
    )

    eq(
        response[
            "status"
        ],
        401,
        "missing Bearer token blocked by existing gateway auth middleware",
    )


def test_gateway_permission_denied():
    worker = manager()

    worker.create_user(
        "u1",
        "normal",
        "Password123",
        roles=[
            "user",
        ],
    )

    token = worker.authenticate(
        "normal",
        "Password123",
        now=100,
    )[
        "token"
    ]

    gateway = APIGateway(
        middleware=[
            GatewayTokenAuthenticationMiddleware(
                auth_manager=worker,
                now_provider=(
                    lambda: 101
                ),
                permission_by_route={
                    (
                        "POST "
                        "/v1/generate"
                    ): (
                        "inference:use"
                    ),
                },
            ),
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
            headers={
                "authorization": (
                    "Bearer "
                    + token
                ),
            },
        )
    )

    eq(
        response[
            "status"
        ],
        403,
        "authenticated user without route permission gets 403",
    )

    eq(
        response[
            "error"
        ][
            "code"
        ],
        "FORBIDDEN",
        "gateway permission error preserved",
    )


def test_validation():
    expect_error(
        ValueError,
        lambda: AuthManager(
            server_secret="short",
        ),
        "short server secret rejected",
    )

    worker = manager()

    expect_error(
        ValueError,
        lambda: worker.create_user(
            "u1",
            "x",
            "short",
        ),
        "short password rejected",
    )

    expect_error(
        TypeError,
        lambda: AuthService(
            worker
        ).handle(
            {}
        ),
        "non-ServiceRequest rejected",
    )


def main():
    test_sha256_vectors()
    test_hmac_vector()
    test_pbkdf2_vector()
    test_user_creation_no_plaintext()
    test_duplicate_identity_validation()
    test_authenticate_verify()
    test_bad_password_and_lock()
    test_expiry()
    test_token_tamper()
    test_revoke()
    test_password_change_revokes_sessions()
    test_disable_user()
    test_permissions_and_roles()
    test_admin_wildcard()
    test_status()
    test_service_flow()
    test_service_errors()
    test_protocol_round_trip()
    test_gateway_authentication_integration()
    test_gateway_missing_token_blocked()
    test_gateway_permission_denied()
    test_validation()

    print(
        "AUTH SERVICE TEST SUITE: PASS"
    )
    print(
        "Assertions passed:",
        ASSERTIONS,
    )
    print(
        "Files validated: 7/7"
    )
    print(
        "From-scratch SHA-256/HMAC/PBKDF2 vectors: VALIDATED"
    )
    print(
        "Password hash/no-plaintext storage: VALIDATED"
    )
    print(
        "Login/lockout/token expiry/revocation: VALIDATED"
    )
    print(
        "Password-change credential invalidation: VALIDATED"
    )
    print(
        "Role/permission authorization: VALIDATED"
    )
    print(
        "Bearer-token API gateway integration: VALIDATED"
    )
    print(
        "Route-level permission enforcement: VALIDATED"
    )
    print(
        "Protocol service operations: VALIDATED"
    )
    print(
        "Third-party dependencies: 0"
    )


main()
