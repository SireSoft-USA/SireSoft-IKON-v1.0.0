import os

SERIAL_BASE = "libs/core/serialization/"
PROTOCOL_BASE = "libs/protocol/"
EVENT_BASE = "services/event_bus/"
SERVICE_BASE = "services/feature_flag_service/"

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
    "rule.py",
    "flag.py",
    "evaluator.py",
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
            "feature_flag_service implementation contains forbidden import: "
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
    "services/feature_flag_service/"
    "_test_flags.sllmffg"
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


def manager(
    event_bus=None,
):
    worker = FeatureFlagManager(
        event_bus=event_bus
    )

    worker.create_flag(
        flag_key="new_rag",
        variants={
            "off": False,
            "on": True,
            "beta": {
                "mode": "beta",
            },
        },
        default_variant="off",
        disabled_variant="off",
    )

    return worker


def test_default_and_disabled():
    worker = manager()

    result = worker.evaluate(
        "new_rag",
        "user-1",
    )

    eq(
        result[
            "variant"
        ],
        "off",
        "default variant returned",
    )

    eq(
        result[
            "reason"
        ],
        "default",
        "default reason returned",
    )

    worker.set_enabled(
        "new_rag",
        False,
    )

    result = worker.evaluate(
        "new_rag",
        "user-1",
    )

    eq(
        result[
            "reason"
        ],
        "flag_disabled",
        "disabled flag reason",
    )


def test_exact_rule():
    worker = manager()

    worker.add_rule(
        "new_rag",
        "admins",
        conditions=[
            {
                "attribute": "role",
                "operator": "eq",
                "value": "admin",
            },
        ],
        variant="on",
    )

    admin = worker.evaluate(
        "new_rag",
        "u1",
        {
            "role": "admin",
        },
    )

    user = worker.evaluate(
        "new_rag",
        "u2",
        {
            "role": "user",
        },
    )

    eq(
        admin[
            "variant"
        ],
        "on",
        "matching fixed rule selects variant",
    )

    eq(
        admin[
            "rule_id"
        ],
        "admins",
        "matching rule ID returned",
    )

    eq(
        user[
            "variant"
        ],
        "off",
        "non-matching user falls to default",
    )


def test_operators():
    worker = manager()

    worker.add_rule(
        "new_rag",
        "multi",
        conditions=[
            {
                "attribute": "country",
                "operator": "in",
                "value": [
                    "PK",
                    "GB",
                ],
            },
            {
                "attribute": "email",
                "operator": "prefix",
                "value": "dev",
            },
            {
                "attribute": "groups",
                "operator": "contains",
                "value": "beta",
            },
        ],
        variant="beta",
    )

    result = worker.evaluate(
        "new_rag",
        "u1",
        {
            "country": "PK",
            "email": "developer@example.com",
            "groups": [
                "users",
                "beta",
            ],
        },
    )

    eq(
        result[
            "variant"
        ],
        "beta",
        "multiple targeting operators match",
    )


def test_rule_order():
    worker = manager()

    worker.add_rule(
        "new_rag",
        "first",
        conditions=[
            {
                "attribute": "role",
                "operator": "eq",
                "value": "admin",
            },
        ],
        variant="beta",
    )

    worker.add_rule(
        "new_rag",
        "second",
        conditions=[
            {
                "attribute": "role",
                "operator": "eq",
                "value": "admin",
            },
        ],
        variant="on",
    )

    result = worker.evaluate(
        "new_rag",
        "u1",
        {
            "role": "admin",
        },
    )

    eq(
        result[
            "rule_id"
        ],
        "first",
        "first matching rule wins",
    )


def test_rollout_deterministic():
    worker = manager()

    worker.add_rule(
        "new_rag",
        "rollout",
        conditions=[],
        rollout_basis_points=5000,
        rollout_variant="on",
        salt="v1",
    )

    first = worker.evaluate(
        "new_rag",
        "stable-user",
    )

    second = worker.evaluate(
        "new_rag",
        "stable-user",
    )

    eq(
        first[
            "variant"
        ],
        second[
            "variant"
        ],
        "same subject gets stable rollout variant",
    )

    eq(
        first[
            "rollout_bucket"
        ],
        second[
            "rollout_bucket"
        ],
        "same subject gets stable rollout bucket",
    )


def test_rollout_boundaries():
    worker_all = manager()

    worker_all.add_rule(
        "new_rag",
        "all",
        rollout_basis_points=10000,
        rollout_variant="on",
    )

    eq(
        worker_all.evaluate(
            "new_rag",
            "any-user",
        )[
            "variant"
        ],
        "on",
        "100 percent rollout always selects variant",
    )

    worker_none = manager()

    worker_none.add_rule(
        "new_rag",
        "none",
        rollout_basis_points=0,
        rollout_variant="on",
    )

    eq(
        worker_none.evaluate(
            "new_rag",
            "any-user",
        )[
            "variant"
        ],
        "off",
        "zero percent rollout falls to default",
    )


def test_rule_remove():
    worker = manager()

    worker.add_rule(
        "new_rag",
        "admins",
        conditions=[
            {
                "attribute": "role",
                "operator": "eq",
                "value": "admin",
            },
        ],
        variant="on",
    )

    worker.remove_rule(
        "new_rag",
        "admins",
    )

    eq(
        worker.evaluate(
            "new_rag",
            "u1",
            {
                "role": "admin",
            },
        )[
            "variant"
        ],
        "off",
        "removed rule no longer applies",
    )


def test_value_copy_isolation():
    worker = manager()

    result = worker.evaluate(
        "new_rag",
        "u1",
    )

    check(
        result[
            "value"
        ] is False,
        "scalar flag value returned",
    )

    beta_worker = FeatureFlagManager()

    beta_worker.create_flag(
        "object_flag",
        variants={
            "control": {
                "mode": "control",
            },
            "beta": {
                "mode": "beta",
                "features": [
                    "x",
                ],
            },
        },
        default_variant="beta",
        disabled_variant="control",
    )

    evaluated = beta_worker.evaluate(
        "object_flag",
        "u",
    )

    evaluated[
        "value"
    ][
        "features"
    ].append(
        "mutated"
    )

    eq(
        beta_worker.evaluate(
            "object_flag",
            "u",
        )[
            "value"
        ][
            "features"
        ],
        [
            "x",
        ],
        "variant object isolated from caller mutation",
    )


def test_event_bus():
    bus = EventBusManager()
    seen = []

    bus.subscribe(
        "flag-events",
        "feature_flag.",
        lambda event: seen.append(
            event.topic
        ),
        mode="prefix",
    )

    worker = FeatureFlagManager(
        event_bus=bus
    )

    worker.create_flag(
        "x",
        {
            "off": False,
            "on": True,
        },
        "off",
        "off",
        timestamp=1,
    )

    worker.set_enabled(
        "x",
        False,
        timestamp=2,
    )

    worker.delete_flag(
        "x",
        timestamp=3,
    )

    eq(
        seen,
        [
            "feature_flag.created",
            "feature_flag.updated",
            "feature_flag.deleted",
        ],
        "flag lifecycle events published",
    )


def test_status_version():
    worker = manager()

    base_version = worker.version

    worker.add_rule(
        "new_rag",
        "r1",
        variant="on",
    )

    worker.evaluate(
        "new_rag",
        "u1",
    )

    status = worker.status()

    eq(
        status[
            "manager_version"
        ],
        base_version + 1,
        "manager version increments on mutation",
    )

    eq(
        status[
            "total_evaluations"
        ],
        1,
        "evaluation count tracked",
    )

    eq(
        status[
            "rule_count"
        ],
        1,
        "rule count tracked",
    )


def test_persistence_round_trip():
    if os.path.exists(
        STATE_PATH
    ):
        os.remove(
            STATE_PATH
        )

    source = manager()

    source.add_rule(
        "new_rag",
        "admins",
        conditions=[
            {
                "attribute": "role",
                "operator": "eq",
                "value": "admin",
            },
        ],
        variant="on",
    )

    source.evaluate(
        "new_rag",
        "u1",
        {
            "role": "admin",
        },
    )

    before = source.export_state()

    saved = source.save_state(
        STATE_PATH
    )

    check(
        saved[
            "bytes"
        ] > 0,
        "feature-flag snapshot written",
    )

    restored = FeatureFlagManager()

    restored.load_state_file(
        STATE_PATH
    )

    eq(
        restored.export_state(),
        before,
        "feature-flag exact state round trip",
    )

    eq(
        restored.evaluate(
            "new_rag",
            "u1",
            {
                "role": "admin",
            },
        )[
            "variant"
        ],
        "on",
        "restored targeting rule evaluates",
    )


def test_persistence_corruption():
    worker = manager()

    worker.save_state(
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
        lambda: FeatureFlagManager().load_state_file(
            STATE_PATH
        ),
        "feature-flag checksum detects corruption",
    )


def test_service_flow():
    service = FeatureFlagService()

    created = service.handle(
        ServiceRequest(
            "f1",
            "feature_flag_service",
            "create_flag",
            payload={
                "flag_key": "new_ui",
                "variants": {
                    "off": False,
                    "on": True,
                },
                "default_variant": "off",
                "disabled_variant": "off",
            },
        )
    )

    eq(
        created.success,
        True,
        "service creates feature flag",
    )

    rule = service.handle(
        ServiceRequest(
            "f2",
            "feature_flag_service",
            "add_rule",
            payload={
                "flag_key": "new_ui",
                "rule_id": "admins",
                "conditions": [
                    {
                        "attribute": "role",
                        "operator": "eq",
                        "value": "admin",
                    },
                ],
                "variant": "on",
            },
        )
    )

    eq(
        rule.success,
        True,
        "service adds targeting rule",
    )

    evaluated = service.handle(
        ServiceRequest(
            "f3",
            "feature_flag_service",
            "evaluate",
            payload={
                "flag_key": "new_ui",
                "subject_key": "u1",
                "attributes": {
                    "role": "admin",
                },
            },
        )
    )

    eq(
        evaluated.data[
            "evaluation"
        ][
            "variant"
        ],
        "on",
        "service evaluates feature flag",
    )


def test_protocol_round_trip():
    worker = manager()

    service = FeatureFlagService(
        worker
    )

    codec = ProtocolCodec()

    request = ServiceRequest(
        "protocol-flag",
        "feature_flag_service",
        "evaluate",
        payload={
            "flag_key": "new_rag",
            "subject_key": "u1",
        },
        trace_id="trace-flag",
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
        "flag evaluation survives protocol codec",
    )

    eq(
        response.trace_id,
        "trace-flag",
        "feature-flag trace preserved",
    )

    eq(
        response.data[
            "evaluation"
        ][
            "variant"
        ],
        "off",
        "evaluation result survives protocol",
    )


def test_errors():
    service = FeatureFlagService()

    missing = service.handle(
        ServiceRequest(
            "e1",
            "feature_flag_service",
            "get_flag",
            payload={
                "flag_key": "missing",
            },
        )
    )

    eq(
        missing.error.code,
        "NOT_FOUND",
        "missing flag maps to NOT_FOUND",
    )

    invalid = service.handle(
        ServiceRequest(
            "e2",
            "feature_flag_service",
            "create_flag",
            payload={
                "flag_key": "x",
                "variants": {
                    "off": False,
                },
                "default_variant": "missing",
                "disabled_variant": "off",
            },
        )
    )

    eq(
        invalid.error.code,
        "INVALID_REQUEST",
        "invalid flag maps to INVALID_REQUEST",
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


def test_validation():
    worker = manager()

    expect_error(
        ValueError,
        lambda: worker.create_flag(
            "new_rag",
            {
                "off": False,
                "on": True,
            },
            "off",
            "off",
        ),
        "duplicate flag rejected",
    )

    expect_error(
        ValueError,
        lambda: worker.add_rule(
            "new_rag",
            "bad",
            variant="missing",
        ),
        "rule referencing unknown variant rejected",
    )

    expect_error(
        ValueError,
        lambda: TargetingRule(
            "bad-rollout",
            rollout_basis_points=10001,
            rollout_variant="on",
        ),
        "rollout above 100 percent rejected",
    )

    expect_error(
        ValueError,
        lambda: TargetingRule(
            "bad-operator",
            conditions=[
                {
                    "attribute": "role",
                    "operator": "unknown",
                    "value": "x",
                },
            ],
            variant="on",
        ),
        "unknown targeting operator rejected",
    )


def main():
    try:
        test_default_and_disabled()
        test_exact_rule()
        test_operators()
        test_rule_order()
        test_rollout_deterministic()
        test_rollout_boundaries()
        test_rule_remove()
        test_value_copy_isolation()
        test_event_bus()
        test_status_version()
        test_persistence_round_trip()
        test_persistence_corruption()
        test_service_flow()
        test_protocol_round_trip()
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
        "FEATURE FLAG SERVICE TEST SUITE: PASS"
    )
    print(
        "Assertions passed:",
        ASSERTIONS,
    )
    print(
        "Files validated: 6/6"
    )
    print(
        "Named variants/default/disabled behavior: VALIDATED"
    )
    print(
        "Ordered attribute targeting rules: VALIDATED"
    )
    print(
        "Deterministic percentage rollout: VALIDATED"
    )
    print(
        "Rule lifecycle/version tracking: VALIDATED"
    )
    print(
        "Event-bus configuration-change publication: VALIDATED"
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
