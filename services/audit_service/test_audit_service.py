import os

SERIAL_BASE = "libs/core/serialization/"
PROTOCOL_BASE = "libs/protocol/"
EVENT_BASE = "services/event_bus/"
SERVICE_BASE = "services/audit_service/"

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
    "record.py",
    "sanitizer.py",
    "ledger.py",
    "persistence.py",
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
            "audit_service implementation contains forbidden import: "
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

STATE_PATH = (
    "services/audit_service/"
    "_test_audit.sllmaud"
)


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


def test_append_chain():
    manager = AuditManager()

    one = manager.record(
        timestamp=1,
        actor_id="u1",
        actor_type="user",
        action="login",
        resource="auth_service",
        outcome="success",
    )

    two = manager.record(
        timestamp=2,
        actor_id="u1",
        actor_type="user",
        action="chat",
        resource="rag_service",
        outcome="success",
    )

    eq(
        one.sequence,
        1,
        "first audit sequence",
    )

    eq(
        two.sequence,
        2,
        "second audit sequence",
    )

    eq(
        one.previous_hash,
        "0",
        "genesis audit record previous hash",
    )

    eq(
        two.previous_hash,
        one.record_hash,
        "second audit links to first hash",
    )

    eq(
        manager.verify()[
            "valid"
        ],
        True,
        "fresh audit chain valid",
    )


def test_hash_deterministic():
    ledger_a = AuditLedger()
    ledger_b = AuditLedger()

    record_a = AuditRecord(
        "a1",
        1,
        10,
        "u1",
        "user",
        "read",
        "document:1",
        "success",
        metadata={
            "b": 2,
            "a": 1,
        },
    )

    record_b = AuditRecord(
        "a1",
        1,
        10,
        "u1",
        "user",
        "read",
        "document:1",
        "success",
        metadata={
            "a": 1,
            "b": 2,
        },
    )

    ledger_a.append(
        record_a
    )

    ledger_b.append(
        record_b
    )

    eq(
        record_a.record_hash,
        record_b.record_hash,
        "dictionary key order does not affect audit hash",
    )


def test_tamper_detection():
    manager = AuditManager()

    manager.record(
        1,
        "u1",
        "user",
        "read",
        "doc",
        "success",
    )

    second = manager.record(
        2,
        "u1",
        "user",
        "update",
        "doc",
        "success",
    )

    second.action = "delete"

    integrity = manager.verify()

    eq(
        integrity[
            "valid"
        ],
        False,
        "mutated audit record breaks integrity",
    )

    eq(
        integrity[
            "reason"
        ],
        "record_hash_mismatch",
        "tamper reason identifies record hash mismatch",
    )


def test_redaction():
    manager = AuditManager()

    record = manager.record(
        timestamp=1,
        actor_id="u1",
        actor_type="user",
        action="login",
        resource="auth_service",
        outcome="success",
        metadata={
            "ip": "127.0.0.1",
            "password": "do-not-store",
            "nested": {
                "token": "secret-token",
                "safe": "ok",
            },
        },
    )

    eq(
        record.metadata[
            "password"
        ],
        "[REDACTED]",
        "password redacted",
    )

    eq(
        record.metadata[
            "nested"
        ][
            "token"
        ],
        "[REDACTED]",
        "nested token redacted",
    )

    check(
        "do-not-store"
        not in repr(
            record.to_dict()
        ),
        "plaintext password absent from audit record",
    )


def test_query_filters():
    manager = AuditManager()

    manager.record(
        10,
        "u1",
        "user",
        "login",
        "auth_service",
        "success",
        trace_id="t1",
    )

    manager.record(
        20,
        "u2",
        "service",
        "generate",
        "inference_service",
        "failure",
        trace_id="t2",
    )

    manager.record(
        30,
        "u1",
        "user",
        "retrieve",
        "retrieval_service",
        "denied",
        trace_id="t3",
    )

    result = manager.query(
        actor_id="u1",
        start_timestamp=15,
        end_timestamp=35,
    )

    eq(
        result[
            "count"
        ],
        1,
        "actor/time filters",
    )

    eq(
        result[
            "records"
        ][0][
            "action"
        ],
        "retrieve",
        "filtered audit record correct",
    )

    newest = manager.query(
        limit=2,
        newest_first=True,
    )

    eq(
        [
            row[
                "sequence"
            ]
            for row in newest[
                "records"
            ]
        ],
        [
            3,
            2,
        ],
        "newest-first audit query",
    )


def test_event_bus_integration():
    event_bus = EventBusManager()
    seen = []

    event_bus.subscribe(
        "audits",
        "audit.",
        lambda event: seen.append(
            event.topic
        ),
        mode="prefix",
    )

    manager = AuditManager(
        event_bus=event_bus
    )

    record = manager.record(
        timestamp=50,
        actor_id="u1",
        actor_type="user",
        action="chat",
        resource="rag_service",
        outcome="success",
        trace_id="trace-audit",
    )

    eq(
        seen,
        [
            "audit.recorded",
        ],
        "audit lifecycle event published",
    )

    history = event_bus.history(
        topic="audit.recorded"
    )

    eq(
        history[
            "events"
        ][0][
            "payload"
        ][
            "record_hash"
        ],
        record.record_hash,
        "audit event includes committed record hash",
    )

    eq(
        history[
            "events"
        ][0][
            "trace_id"
        ],
        "trace-audit",
        "audit trace propagated",
    )


def test_status():
    manager = AuditManager()

    manager.record(
        1,
        "u1",
        "user",
        "a",
        "r",
        "success",
    )

    manager.record(
        2,
        "u2",
        "user",
        "b",
        "r",
        "denied",
    )

    status = manager.status()

    eq(
        status[
            "ready"
        ],
        True,
        "valid audit ledger ready",
    )

    eq(
        status[
            "record_count"
        ],
        2,
        "status record count",
    )

    eq(
        status[
            "outcomes"
        ][
            "success"
        ],
        1,
        "status success count",
    )

    eq(
        status[
            "outcomes"
        ][
            "denied"
        ],
        1,
        "status denied count",
    )

    eq(
        status[
            "integrity_scheme"
        ],
        "fnv1a64_hash_chain",
        "status accurately names integrity scheme",
    )


def test_persistence_round_trip():
    if os.path.exists(
        STATE_PATH
    ):
        os.remove(
            STATE_PATH
        )

    source = AuditManager()

    source.record(
        1,
        "admin",
        "user",
        "promote_model",
        "model:v1",
        "success",
        metadata={
            "stage": "production",
        },
    )

    source.record(
        2,
        "svc",
        "service",
        "generate",
        "model:v1",
        "success",
    )

    before = source.export_state()

    saved = source.save_state(
        STATE_PATH
    )

    check(
        saved[
            "bytes"
        ] > 0,
        "audit snapshot written",
    )

    restored = AuditManager()

    restored.load_state_file(
        STATE_PATH
    )

    eq(
        restored.export_state(),
        before,
        "audit state exact round trip",
    )

    eq(
        restored.verify()[
            "valid"
        ],
        True,
        "restored audit chain valid",
    )

    next_record = restored.record(
        3,
        "u3",
        "user",
        "login",
        "auth_service",
        "success",
    )

    eq(
        next_record.sequence,
        3,
        "audit sequence resumes after restore",
    )


def test_persistence_corruption():
    manager = AuditManager()

    manager.record(
        1,
        "u",
        "user",
        "read",
        "r",
        "success",
    )

    manager.save_state(
        STATE_PATH
    )

    handle = open(
        STATE_PATH,
        "rb",
    )

    try:
        data = bytearray(
            handle.read()
        )
    finally:
        handle.close()

    data[
        -1
    ] ^= 0x01

    handle = open(
        STATE_PATH,
        "wb",
    )

    try:
        handle.write(
            data
        )
    finally:
        handle.close()

    expect_error(
        ValueError,
        lambda: AuditManager().load_state_file(
            STATE_PATH
        ),
        "audit snapshot checksum detects corruption",
    )


def test_service_flow():
    service = AuditService()

    response = service.handle(
        ServiceRequest(
            "a1",
            "audit_service",
            "record",
            payload={
                "timestamp": 100,
                "actor_id": "u1",
                "actor_type": "user",
                "action": "login",
                "resource": "auth_service",
                "outcome": "success",
                "metadata": {
                    "token": "hide-this",
                },
            },
            trace_id="trace-service-audit",
        )
    )

    eq(
        response.success,
        True,
        "audit service records event",
    )

    audit = response.data[
        "audit"
    ]

    eq(
        audit[
            "trace_id"
        ],
        "trace-service-audit",
        "service trace propagated",
    )

    eq(
        audit[
            "metadata"
        ][
            "token"
        ],
        "[REDACTED]",
        "service audit metadata sanitized",
    )

    verified = service.handle(
        ServiceRequest(
            "a2",
            "audit_service",
            "verify",
        )
    )

    eq(
        verified.data[
            "integrity"
        ][
            "valid"
        ],
        True,
        "service verifies ledger integrity",
    )


def test_protocol_round_trip():
    service = AuditService()
    codec = ProtocolCodec()

    request = ServiceRequest(
        "protocol-audit",
        "audit_service",
        "record",
        payload={
            "timestamp": 5,
            "actor_id": "svc",
            "actor_type": "service",
            "action": "retrieve",
            "resource": "index",
            "outcome": "success",
        },
        trace_id="trace-audit-protocol",
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
        "audit record survives protocol codec",
    )

    eq(
        response.trace_id,
        "trace-audit-protocol",
        "audit protocol trace preserved",
    )

    check(
        response.data[
            "audit"
        ][
            "record_hash"
        ]
        is not None,
        "record hash survives protocol",
    )


def test_append_only_surface():
    service = AuditService()

    response = service.handle(
        ServiceRequest(
            "x",
            "audit_service",
            "clear",
        )
    )

    eq(
        response.error.code,
        "INVALID_REQUEST",
        "audit service exposes no clear operation",
    )


def test_errors():
    service = AuditService()

    missing = service.handle(
        ServiceRequest(
            "m",
            "audit_service",
            "get",
            payload={
                "audit_id": "missing",
            },
        )
    )

    eq(
        missing.error.code,
        "NOT_FOUND",
        "missing audit record maps to NOT_FOUND",
    )

    invalid = service.handle(
        ServiceRequest(
            "i",
            "audit_service",
            "record",
            payload={
                "timestamp": 1,
                "actor_id": "u",
                "actor_type": "user",
                "action": "x",
                "resource": "r",
                "outcome": "not-valid",
            },
        )
    )

    eq(
        invalid.error.code,
        "INVALID_REQUEST",
        "invalid audit outcome rejected",
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


def test_validation():
    ledger = AuditLedger()

    first = AuditRecord(
        "a1",
        1,
        1,
        "u",
        "user",
        "x",
        "r",
        "success",
    )

    ledger.append(
        first
    )

    duplicate = AuditRecord(
        "a1",
        2,
        2,
        "u",
        "user",
        "y",
        "r",
        "success",
        previous_hash=(
            first.record_hash
        ),
    )

    expect_error(
        ValueError,
        lambda: ledger.append(
            duplicate
        ),
        "duplicate audit ID rejected",
    )

    bad_sequence = AuditRecord(
        "a2",
        3,
        2,
        "u",
        "user",
        "z",
        "r",
        "success",
        previous_hash=(
            first.record_hash
        ),
    )

    expect_error(
        ValueError,
        lambda: ledger.append(
            bad_sequence
        ),
        "non-contiguous audit sequence rejected",
    )


def main():
    try:
        test_append_chain()
        test_hash_deterministic()
        test_tamper_detection()
        test_redaction()
        test_query_filters()
        test_event_bus_integration()
        test_status()
        test_persistence_round_trip()
        test_persistence_corruption()
        test_service_flow()
        test_protocol_round_trip()
        test_append_only_surface()
        test_errors()
        test_validation()

    finally:
        if os.path.exists(
            STATE_PATH
        ):
            os.remove(
                STATE_PATH
            )

    print(
        "AUDIT SERVICE TEST SUITE: PASS"
    )
    print(
        "Assertions passed:",
        ASSERTIONS,
    )
    print(
        "Files validated: 6/6"
    )
    print(
        "Append-only audit sequencing: VALIDATED"
    )
    print(
        "Deterministic hash-chain integrity: VALIDATED"
    )
    print(
        "Tamper detection: VALIDATED"
    )
    print(
        "Sensitive metadata redaction: VALIDATED"
    )
    print(
        "Audit querying/filtering: VALIDATED"
    )
    print(
        "Event-bus lifecycle publication: VALIDATED"
    )
    print(
        "Checksum-protected binary persistence: VALIDATED"
    )
    print(
        "Protocol service operations: VALIDATED"
    )
    print(
        "Third-party dependencies: 0"
    )


main()
