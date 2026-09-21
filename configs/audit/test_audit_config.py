import os

SERIAL_BASE = "libs/core/serialization/"
PARSER_BASE = "libs/data/parsers/"
PROTOCOL_BASE = "libs/protocol/"
EVENT_BASE = "services/event_bus/"
AUDIT_BASE = "services/audit_service/"
CONFIG_BASE = "configs/audit/"

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
        PARSER_BASE,
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
        ],
    ),
    (
        EVENT_BASE,
        [
            "event.py",
            "subscription.py",
            "manager.py",
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
    "persistence.py",
    "policy.py",
    "config.py",
    "defaults.py",
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
            "audit config implementation contains forbidden import: "
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
    "configs/audit/"
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
        + repr(expected),
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


def cleanup():
    if os.path.isfile(
        STATE_PATH
    ):
        os.remove(
            STATE_PATH
        )


def sample_config(
    attach_event_bus=False,
    load=False,
):
    return AuditConfig(
        policy=AuditPolicyConfig(
            require_metadata_sanitization=True,
            expected_integrity_scheme=(
                "fnv1a64_hash_chain"
            ),
            require_append_only=True,
        ),
        persistence=(
            AuditPersistenceConfig(
                state_path=STATE_PATH,
                load_state_on_start=load,
            )
        ),
        attach_event_bus=(
            attach_event_bus
        ),
        metadata={
            "profile": "runtime",
        },
    )


def test_policy_config():
    policy = AuditPolicyConfig()

    eq(
        policy.expected_integrity_scheme,
        "fnv1a64_hash_chain",
        "audit integrity scheme stored",
    )

    eq(
        policy.require_append_only,
        True,
        "append-only expectation enabled",
    )

    expect_error(
        ValueError,
        lambda: AuditPolicyConfig(
            expected_integrity_scheme=(
                "sha999"
            )
        ),
        "unsupported integrity scheme rejected",
    )


def test_defaults():
    config = default_audit_config()

    eq(
        config.attach_event_bus,
        True,
        "default audit config attaches event bus",
    )

    eq(
        config.policy.require_metadata_sanitization,
        True,
        "default audit config requires sanitization",
    )

    eq(
        config.persistence.state_path,
        (
            "runtime/state/"
            "audit.sllmaud"
        ),
        "default audit persistence path",
    )


def test_codec():
    text = (
        '{"policy":{'
        '"require_metadata_sanitization":true,'
        '"expected_integrity_scheme":"fnv1a64_hash_chain",'
        '"require_append_only":true'
        '},'
        '"persistence":{'
        '"state_path":"state/audit.bin",'
        '"load_state_on_start":false'
        '},'
        '"attach_event_bus":false,'
        '"metadata":{"profile":"prod"}'
        '}'
    )

    config = (
        AuditConfigCodec()
        .decode_text(
            text
        )
    )

    eq(
        config.persistence.state_path,
        "state/audit.bin",
        "codec audit state path",
    )

    eq(
        config.policy.require_append_only,
        True,
        "codec append-only policy",
    )

    eq(
        config.metadata["profile"],
        "prod",
        "codec metadata",
    )


def test_validator():
    config = AuditConfig(
        policy=AuditPolicyConfig(
            require_metadata_sanitization=False,
            require_append_only=False,
        ),
        persistence=(
            AuditPersistenceConfig(
                state_path="audit.bin",
                load_state_on_start=False,
            )
        ),
    )

    result = (
        AuditConfigValidator()
        .validate(
            config
        )
    )

    codes = [
        item["code"]
        for item
        in result["warnings"]
    ]

    check(
        "AUDIT_SANITIZATION_EXPECTATION_DISABLED"
        in codes,
        "disabled sanitization expectation warned",
    )

    check(
        "AUDIT_APPEND_ONLY_EXPECTATION_DISABLED"
        in codes,
        "disabled append-only expectation warned",
    )

    check(
        "AUDIT_STATE_NOT_AUTO_LOADED"
        in codes,
        "configured non-auto-loaded state warned",
    )


def test_manager_generation():
    manager = (
        AuditConfigFactory()
        .build_manager(
            sample_config()
        )
    )

    check(
        isinstance(
            manager,
            AuditManager,
        ),
        "factory creates AuditManager",
    )

    status = manager.status()

    eq(
        status["ready"],
        True,
        "fresh configured audit manager ready",
    )

    eq(
        status["integrity_scheme"],
        "fnv1a64_hash_chain",
        "runtime integrity scheme matches config",
    )


def test_secret_redaction():
    manager = (
        AuditConfigFactory()
        .build_manager(
            sample_config()
        )
    )

    record = manager.record(
        timestamp=1,
        actor_id="user-1",
        actor_type="user",
        action="login",
        resource="session",
        outcome="success",
        metadata={
            "token": "secret-token",
            "nested": {
                "password": "secret-pass",
                "safe": "value",
            },
        },
    )

    eq(
        record.metadata["token"],
        "[REDACTED]",
        "top-level token redacted",
    )

    eq(
        record.metadata[
            "nested"
        ][
            "password"
        ],
        "[REDACTED]",
        "nested password redacted",
    )

    eq(
        record.metadata[
            "nested"
        ][
            "safe"
        ],
        "value",
        "non-secret audit metadata preserved",
    )


def test_hash_chain_and_query():
    manager = (
        AuditConfigFactory()
        .build_manager(
            sample_config()
        )
    )

    first = manager.record(
        10,
        "user-1",
        "user",
        "read",
        "document:1",
        outcome="success",
        trace_id="trace-a",
    )

    second = manager.record(
        11,
        "user-1",
        "user",
        "delete",
        "document:2",
        outcome="denied",
        trace_id="trace-a",
    )

    eq(
        second.previous_hash,
        first.record_hash,
        "audit records link to previous hash",
    )

    integrity = manager.verify()

    eq(
        integrity["valid"],
        True,
        "configured audit chain verifies",
    )

    eq(
        integrity["record_count"],
        2,
        "audit integrity reports record count",
    )

    result = manager.query(
        actor_id="user-1",
        outcome="denied",
        limit=10,
    )

    eq(
        result["count"],
        1,
        "audit query filters configured ledger",
    )

    eq(
        result["records"][0][
            "action"
        ],
        "delete",
        "audit query returns expected record",
    )


def test_tamper_detection():
    manager = (
        AuditConfigFactory()
        .build_manager(
            sample_config()
        )
    )

    manager.record(
        1,
        "admin",
        "user",
        "update",
        "model",
        outcome="success",
    )

    record = manager.ledger.records()[0]
    record.action = "tampered"

    integrity = manager.verify()

    eq(
        integrity["valid"],
        False,
        "mutated audit record breaks hash chain",
    )

    eq(
        integrity["reason"],
        "record_hash_mismatch",
        "tamper reason exposed",
    )


def test_event_bus_integration():
    bus = EventBusManager(
        max_history=10
    )

    manager = (
        AuditConfigFactory()
        .build_manager(
            sample_config(
                attach_event_bus=True
            ),
            event_bus=bus,
        )
    )

    record = manager.record(
        timestamp=100,
        actor_id="service-a",
        actor_type="service",
        action="promote",
        resource="model:v1",
        outcome="success",
        trace_id="trace-1",
        correlation_id="corr-1",
    )

    history = bus.history(
        limit=10
    )

    eq(
        history["count"],
        1,
        "audit commit publishes one event",
    )

    eq(
        history["events"][0][
            "topic"
        ],
        "audit.recorded",
        "audit event topic",
    )

    eq(
        history["events"][0][
            "payload"
        ][
            "record_hash"
        ],
        record.record_hash,
        "audit event includes committed record hash",
    )

    eq(
        history["events"][0][
            "trace_id"
        ],
        "trace-1",
        "audit event preserves trace",
    )


def test_missing_event_bus():
    expect_error(
        ValueError,
        lambda: (
            AuditConfigFactory()
            .build_manager(
                sample_config(
                    attach_event_bus=True
                )
            )
        ),
        "required audit event bus enforced",
    )


def test_persistence_round_trip():
    cleanup()

    manager = (
        AuditConfigFactory()
        .build_manager(
            sample_config()
        )
    )

    manager.record(
        1,
        "user-1",
        "user",
        "chat",
        "conversation:1",
        outcome="success",
        metadata={
            "authorization": "Bearer secret",
            "message_count": 3,
        },
    )

    artifact = (
        AuditConfigFactory()
        .save_state(
            manager,
            sample_config(),
        )
    )

    check(
        artifact["bytes"] > 0,
        "audit snapshot persisted",
    )

    loaded = (
        AuditConfigFactory()
        .build_manager(
            sample_config(
                load=True
            )
        )
    )

    eq(
        loaded.export_state(),
        manager.export_state(),
        "configured startup load restores exact audit state",
    )

    eq(
        loaded.verify()["valid"],
        True,
        "restored audit state preserves integrity",
    )


def test_corruption_boundary():
    cleanup()

    manager = (
        AuditConfigFactory()
        .build_manager(
            sample_config()
        )
    )

    manager.record(
        1,
        "service",
        "service",
        "write",
        "resource",
        outcome="success",
    )

    AuditConfigFactory().save_state(
        manager,
        sample_config(),
    )

    raw = open(
        STATE_PATH,
        "rb",
    ).read()

    damaged = bytearray(raw)
    damaged[-1] ^= 1

    open(
        STATE_PATH,
        "wb",
    ).write(
        bytes(damaged)
    )

    expect_error(
        ValueError,
        lambda: (
            AuditConfigFactory()
            .build_manager(
                sample_config(
                    load=True
                )
            )
        ),
        "corrupted audit snapshot rejected",
    )


def test_service_creation():
    service = (
        AuditConfigFactory()
        .build_service(
            sample_config()
        )
    )

    check(
        isinstance(
            service,
            AuditService,
        ),
        "factory creates AuditService",
    )

    recorded = service.handle(
        ServiceRequest(
            "audit-record",
            "audit_service",
            "record",
            payload={
                "timestamp": 50,
                "actor_id": "user-2",
                "actor_type": "user",
                "action": "generate",
                "resource": "chat",
                "outcome": "success",
                "metadata": {
                    "api_key": "hidden",
                },
            },
            trace_id="trace-service",
        )
    )

    eq(
        recorded.success,
        True,
        "configured audit service records",
    )

    eq(
        recorded.data["audit"][
            "metadata"
        ][
            "api_key"
        ],
        "[REDACTED]",
        "protocol audit write sanitizes secret metadata",
    )

    eq(
        recorded.data["audit"][
            "trace_id"
        ],
        "trace-service",
        "protocol trace copied into audit record",
    )

    verify = service.handle(
        ServiceRequest(
            "audit-verify",
            "audit_service",
            "verify",
        )
    )

    eq(
        verify.data["integrity"][
            "valid"
        ],
        True,
        "configured audit service verifies ledger",
    )


def test_append_only_surface():
    service = (
        AuditConfigFactory()
        .build_service(
            sample_config()
        )
    )

    response = service.handle(
        ServiceRequest(
            "audit-delete",
            "audit_service",
            "delete",
            payload={
                "audit_id": "audit-1",
            },
        )
    )

    eq(
        response.success,
        False,
        "audit protocol exposes no delete operation",
    )

    eq(
        response.error.code,
        "INVALID_REQUEST",
        "append-only boundary rejects delete",
    )


def main():
    cleanup()

    try:
        test_policy_config()
        test_defaults()
        test_codec()
        test_validator()
        test_manager_generation()
        test_secret_redaction()
        test_hash_chain_and_query()
        test_tamper_detection()
        test_event_bus_integration()
        test_missing_event_bus()
        test_persistence_round_trip()
        test_corruption_boundary()
        test_service_creation()
        test_append_only_surface()

    finally:
        cleanup()

    print(
        "AUDIT CONFIG TEST SUITE: PASS"
    )
    print(
        "Assertions passed:",
        ASSERTIONS,
    )
    print(
        "Files validated: 7/7"
    )
    print(
        "Typed audit policy/persistence config: VALIDATED"
    )
    print(
        "Handwritten JSON decoding: VALIDATED"
    )
    print(
        "Secret-bearing metadata sanitization: VALIDATED"
    )
    print(
        "Append-only audit boundary: VALIDATED"
    )
    print(
        "Linked record integrity/tamper detection: VALIDATED"
    )
    print(
        "EventBus audit lifecycle integration: VALIDATED"
    )
    print(
        "Binary snapshot/checksum restore: VALIDATED"
    )
    print(
        "AuditService generation: VALIDATED"
    )
    print(
        "Third-party dependencies: 0"
    )


main()
