SERIAL_BASE = "libs/core/serialization/"
PROTOCOL_BASE = "libs/protocol/"
EVENT_BASE = "services/event_bus/"
AUDIT_BASE = "services/audit_service/"
SERVICE_BASE = "services/secret_service/"

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
        EVENT_BASE,
        [
            "event.py",
            "subscription.py",
            "manager.py",
            "service.py",
        ],
    ),
    (
        AUDIT_BASE,
        [
            "record.py",
            "sanitizer.py",
            "ledger.py",
            "persistence.py",
            "manager.py",
            "service.py",
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
    "secret.py",
    "sanitizer.py",
    "manager.py",
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
            "secret_service implementation contains forbidden import: "
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


def build():
    bus = EventBusManager()
    audit = AuditManager()

    manager = SecretManager(
        event_bus=bus,
        audit_manager=audit,
    )

    return (
        manager,
        bus,
        audit,
    )


def test_create_redaction():
    manager, _, _ = build()

    record = manager.create_secret(
        secret_id="db_password",
        value="super-secret-value",
        actor_id="admin",
        now=1,
        readers=[
            "runtime",
        ],
        writers=[
            "operator",
        ],
        metadata={
            "owner": "database",
            "token": "do-not-store-here",
        },
    )

    public = record.public_dict()

    check(
        "super-secret-value"
        not in repr(
            public
        ),
        "public secret view never exposes raw value",
    )

    eq(
        public[
            "versions"
        ][0][
            "value"
        ],
        "[REDACTED]",
        "version value is explicitly redacted",
    )

    eq(
        public[
            "metadata"
        ][
            "token"
        ],
        "[REDACTED]",
        "secret-bearing metadata is redacted",
    )

    eq(
        public[
            "policy"
        ][
            "admins"
        ],
        [
            "admin",
        ],
        "creator becomes admin",
    )


def test_read_acl():
    manager, _, _ = build()

    manager.create_secret(
        "api_key",
        "key-123",
        "admin",
        1,
        readers=[
            "inference",
        ],
    )

    value = manager.resolve_secret(
        "api_key",
        "inference",
        2,
        purpose="runtime",
    )

    eq(
        value,
        "key-123",
        "authorized internal reader resolves raw secret",
    )

    expect_error(
        PermissionError,
        lambda: manager.resolve_secret(
            "api_key",
            "other",
            3,
        ),
        "unauthorized principal cannot resolve secret",
    )

    eq(
        manager.status()[
            "total_denied_reads"
        ],
        1,
        "denied read counted",
    )


def test_write_acl_rotation():
    manager, _, _ = build()

    manager.create_secret(
        "token",
        "v1",
        "admin",
        1,
        writers=[
            "rotator",
        ],
        readers=[
            "runtime",
        ],
    )

    version = manager.rotate_secret(
        "token",
        "v2",
        "rotator",
        2,
    )

    eq(
        version.version,
        2,
        "rotation creates second version",
    )

    eq(
        manager.resolve_secret(
            "token",
            "runtime",
            3,
        ),
        "v2",
        "current secret resolves rotated value",
    )

    eq(
        manager.resolve_secret(
            "token",
            "runtime",
            4,
            version=1,
        ),
        "v1",
        "authorized reader can resolve retained historical version",
    )

    expect_error(
        PermissionError,
        lambda: manager.rotate_secret(
            "token",
            "v3",
            "runtime",
            5,
        ),
        "read-only principal cannot rotate secret",
    )


def test_policy_admin():
    manager, _, _ = build()

    manager.create_secret(
        "x",
        "value",
        "admin",
        1,
    )

    manager.set_policy(
        "x",
        "admin",
        2,
        readers=[
            "service-a",
        ],
        writers=[
            "service-b",
        ],
        admins=[
            "admin",
            "security-admin",
        ],
    )

    eq(
        manager.check_access(
            "x",
            "service-a",
            "read",
        )[
            "allowed"
        ],
        True,
        "reader access granted",
    )

    eq(
        manager.check_access(
            "x",
            "service-b",
            "write",
        )[
            "allowed"
        ],
        True,
        "writer access granted",
    )

    eq(
        manager.check_access(
            "x",
            "security-admin",
            "admin",
        )[
            "allowed"
        ],
        True,
        "admin access granted",
    )

    expect_error(
        PermissionError,
        lambda: manager.set_policy(
            "x",
            "service-a",
            3,
            readers=[],
        ),
        "non-admin cannot change policy",
    )


def test_actor_cannot_remove_self_admin():
    manager, _, _ = build()

    manager.create_secret(
        "x",
        "value",
        "admin",
        1,
    )

    expect_error(
        ValueError,
        lambda: manager.set_policy(
            "x",
            "admin",
            2,
            admins=[
                "other-admin",
            ],
        ),
        "acting admin cannot remove own admin access",
    )


def test_disable_enable():
    manager, _, _ = build()

    manager.create_secret(
        "x",
        "value",
        "admin",
        1,
        readers=[
            "reader",
        ],
    )

    manager.disable_secret(
        "x",
        "admin",
        2,
    )

    expect_error(
        RuntimeError,
        lambda: manager.resolve_secret(
            "x",
            "reader",
            3,
        ),
        "disabled secret cannot be resolved",
    )

    eq(
        manager.check_access(
            "x",
            "reader",
            "read",
        )[
            "allowed"
        ],
        False,
        "disabled secret check_access reports false",
    )

    manager.enable_secret(
        "x",
        "admin",
        4,
    )

    eq(
        manager.resolve_secret(
            "x",
            "reader",
            5,
        ),
        "value",
        "reenabled secret resolves",
    )


def test_destroy():
    manager, _, _ = build()

    manager.create_secret(
        "x",
        "value",
        "admin",
        1,
        readers=[
            "reader",
        ],
    )

    manager.destroy_secret(
        "x",
        "admin",
        2,
    )

    public = manager.public_get(
        "x"
    )

    eq(
        public[
            "destroyed"
        ],
        True,
        "secret tombstone marked destroyed",
    )

    eq(
        public[
            "current_version"
        ],
        None,
        "destroy removes current version pointer",
    )

    expect_error(
        RuntimeError,
        lambda: manager.resolve_secret(
            "x",
            "reader",
            3,
        ),
        "destroyed secret cannot be resolved",
    )

    expect_error(
        RuntimeError,
        lambda: manager.enable_secret(
            "x",
            "admin",
            4,
        ),
        "destroyed secret cannot be reenabled",
    )


def test_event_bus_never_leaks_value():
    manager, bus, _ = build()

    manager.create_secret(
        "x",
        "raw-secret",
        "admin",
        1,
        readers=[
            "runtime",
        ],
    )

    manager.resolve_secret(
        "x",
        "runtime",
        2,
        purpose="generation",
        trace_id="trace-secret",
    )

    manager.rotate_secret(
        "x",
        "new-raw-secret",
        "admin",
        3,
    )

    history = bus.history(
        limit=100
    )

    text = repr(
        history
    )

    check(
        "raw-secret"
        not in text,
        "event bus never receives original raw secret",
    )

    check(
        "new-raw-secret"
        not in text,
        "event bus never receives rotated raw secret",
    )

    eq(
        history[
            "events"
        ][1][
            "trace_id"
        ],
        "trace-secret",
        "secret access trace propagated to event bus",
    )


def test_audit_never_leaks_value():
    manager, _, audit = build()

    manager.create_secret(
        "x",
        "audit-secret",
        "admin",
        1,
        readers=[
            "runtime",
        ],
    )

    manager.resolve_secret(
        "x",
        "runtime",
        2,
        purpose="inference",
    )

    manager.rotate_secret(
        "x",
        "audit-secret-2",
        "admin",
        3,
    )

    query = audit.query(
        limit=100
    )

    text = repr(
        query
    )

    check(
        "audit-secret"
        not in text,
        "audit ledger never receives raw secret values",
    )

    eq(
        query[
            "count"
        ],
        3,
        "secret create/read/rotate are audited",
    )


def test_service_no_resolve():
    manager, _, _ = build()

    service = SecretService(
        manager
    )

    created = service.handle(
        ServiceRequest(
            "s1",
            "secret_service",
            "create",
            payload={
                "secret_id": "x",
                "value": "never-return-this",
                "actor_id": "admin",
                "now": 1,
                "readers": [
                    "runtime",
                ],
            },
        )
    )

    eq(
        created.success,
        True,
        "service creates secret",
    )

    check(
        "never-return-this"
        not in repr(
            created.data
        ),
        "create response never returns raw value",
    )

    unsupported = service.handle(
        ServiceRequest(
            "s2",
            "secret_service",
            "resolve",
            payload={
                "secret_id": "x",
                "actor_id": "runtime",
                "now": 2,
            },
        )
    )

    eq(
        unsupported.error.code,
        "INVALID_REQUEST",
        "raw secret resolution is not exposed over protocol",
    )


def test_service_rotate_redacted():
    manager, _, _ = build()

    manager.create_secret(
        "x",
        "v1",
        "admin",
        1,
        writers=[
            "rotator",
        ],
    )

    service = SecretService(
        manager
    )

    response = service.handle(
        ServiceRequest(
            "r1",
            "secret_service",
            "rotate",
            payload={
                "secret_id": "x",
                "value": "v2-secret",
                "actor_id": "rotator",
                "now": 2,
            },
        )
    )

    eq(
        response.success,
        True,
        "service rotates secret",
    )

    check(
        "v2-secret"
        not in repr(
            response.data
        ),
        "rotate response never returns raw secret",
    )


def test_protocol_round_trip():
    manager, _, _ = build()
    service = SecretService(
        manager
    )
    codec = ProtocolCodec()

    request = ServiceRequest(
        "protocol-secret",
        "secret_service",
        "create",
        payload={
            "secret_id": "api",
            "value": "protocol-secret-value",
            "actor_id": "admin",
            "now": 1,
        },
        trace_id="trace-secret-protocol",
    )

    request = codec.decode_request(
        codec.encode_request(
            request
        )
    )

    response = service.handle(
        request
    )

    response = codec.decode_response(
        codec.encode_response(
            response
        )
    )

    eq(
        response.success,
        True,
        "secret administration survives protocol codec",
    )

    eq(
        response.trace_id,
        "trace-secret-protocol",
        "secret service trace preserved",
    )

    check(
        "protocol-secret-value"
        not in repr(
            response.data
        ),
        "protocol response does not expose submitted secret",
    )


def test_status():
    manager, _, _ = build()

    manager.create_secret(
        "a",
        "1",
        "admin",
        1,
    )

    manager.create_secret(
        "b",
        "2",
        "admin",
        1,
    )

    manager.disable_secret(
        "b",
        "admin",
        2,
    )

    status = manager.status()

    eq(
        status[
            "storage_mode"
        ],
        "in_memory_only",
        "status accurately reports non-persistent secret storage",
    )

    eq(
        status[
            "secret_count"
        ],
        2,
        "status secret count",
    )

    eq(
        status[
            "enabled_secrets"
        ],
        1,
        "status enabled count",
    )

    eq(
        status[
            "disabled_secrets"
        ],
        1,
        "status disabled count",
    )

    eq(
        status[
            "audit_attached"
        ],
        True,
        "status audit integration",
    )


def test_errors():
    service = SecretService()

    missing = service.handle(
        ServiceRequest(
            "e1",
            "secret_service",
            "get",
            payload={
                "secret_id": "missing",
            },
        )
    )

    eq(
        missing.error.code,
        "NOT_FOUND",
        "missing secret maps to NOT_FOUND",
    )

    invalid = service.handle(
        ServiceRequest(
            "e2",
            "secret_service",
            "create",
            payload={
                "secret_id": "x",
                "value": "",
                "actor_id": "admin",
                "now": 1,
            },
        )
    )

    eq(
        invalid.error.code,
        "INVALID_REQUEST",
        "empty secret value rejected",
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
        "wrong target rejected",
    )

    expect_error(
        TypeError,
        lambda: service.handle(
            {}
        ),
        "non-ServiceRequest rejected",
    )


def test_wildcard_policy():
    manager, _, _ = build()

    manager.create_secret(
        "public-runtime-secret",
        "x",
        "admin",
        1,
        readers=[
            "*",
        ],
    )

    eq(
        manager.resolve_secret(
            "public-runtime-secret",
            "any-service",
            2,
        ),
        "x",
        "wildcard read policy works",
    )


def main():
    test_create_redaction()
    test_read_acl()
    test_write_acl_rotation()
    test_policy_admin()
    test_actor_cannot_remove_self_admin()
    test_disable_enable()
    test_destroy()
    test_event_bus_never_leaks_value()
    test_audit_never_leaks_value()
    test_service_no_resolve()
    test_service_rotate_redacted()
    test_protocol_round_trip()
    test_status()
    test_errors()
    test_wildcard_policy()

    print(
        "SECRET SERVICE TEST SUITE: PASS"
    )
    print(
        "Assertions passed:",
        ASSERTIONS,
    )
    print(
        "Files validated: 5/5"
    )
    print(
        "Versioned in-memory secret storage: VALIDATED"
    )
    print(
        "Reader/writer/admin ACL enforcement: VALIDATED"
    )
    print(
        "Secret rotation/disable/destroy lifecycle: VALIDATED"
    )
    print(
        "Public/protocol redaction boundaries: VALIDATED"
    )
    print(
        "Event-bus leak prevention: VALIDATED"
    )
    print(
        "Audit-service integration without secret leakage: VALIDATED"
    )
    print(
        "Internal-only raw secret resolution: VALIDATED"
    )
    print(
        "Third-party dependencies: 0"
    )


main()
