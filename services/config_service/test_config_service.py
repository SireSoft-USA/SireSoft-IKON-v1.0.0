import os

SERIAL_BASE = "libs/core/serialization/"
PROTOCOL_BASE = "libs/protocol/"
SERVICE_BASE = "services/config_service/"

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
    "schema.py",
    "layer.py",
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
            "config_service implementation contains forbidden import: "
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
    "services/config_service/"
    "_test_config.sllmcfg"
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


def schema():
    result = ConfigSchema(
        "test-schema"
    )

    result.add_field(
        ConfigField(
            "environment",
            "str",
            required=True,
            default="development",
            choices=[
                "development",
                "production",
            ],
        )
    )

    result.add_field(
        ConfigField(
            "port",
            "int",
            required=True,
            default=8000,
            minimum=1,
            maximum=65535,
        )
    )

    result.add_field(
        ConfigField(
            "temperature",
            "float",
            required=True,
            default=1.0,
            minimum=0.0,
            maximum=2.0,
        )
    )

    result.add_field(
        ConfigField(
            "debug",
            "bool",
            required=True,
            default=False,
        )
    )

    result.add_field(
        ConfigField(
            "features",
            "list",
            default=[],
        )
    )

    result.add_field(
        ConfigField(
            "routing",
            "dict",
            default={},
        )
    )

    result.add_field(
        ConfigField(
            "server_secret",
            "str",
            secret=True,
        )
    )

    return result


def manager():
    return ConfigManager(
        schema=schema()
    )


def test_defaults():
    worker = manager()

    resolved = (
        worker.resolve_internal()
    )

    eq(
        resolved[
            "environment"
        ],
        "development",
        "schema default environment",
    )

    eq(
        resolved[
            "port"
        ],
        8000,
        "schema default port",
    )

    eq(
        worker.source_layer(
            "port"
        ),
        "schema_default",
        "default source attribution",
    )


def test_layer_precedence():
    worker = manager()

    worker.add_layer(
        "file",
        priority=10,
        values={
            "port": 9000,
            "debug": True,
        },
    )

    worker.add_layer(
        "runtime",
        priority=100,
        values={
            "port": 9100,
        },
    )

    resolved = (
        worker.resolve_internal()
    )

    eq(
        resolved[
            "port"
        ],
        9100,
        "higher-priority layer wins",
    )

    eq(
        resolved[
            "debug"
        ],
        True,
        "lower layer survives when not overridden",
    )

    eq(
        worker.source_layer(
            "port"
        ),
        "runtime",
        "source layer attribution",
    )


def test_same_priority_insertion_order():
    worker = manager()

    worker.add_layer(
        "one",
        10,
        values={
            "port": 8100,
        },
    )

    worker.add_layer(
        "two",
        10,
        values={
            "port": 8200,
        },
    )

    eq(
        worker.get_internal(
            "port"
        ),
        8200,
        "later same-priority layer wins deterministically",
    )


def test_validation_types_constraints():
    worker = manager()

    expect_error(
        TypeError,
        lambda: worker.add_layer(
            "bad-type",
            1,
            values={
                "port": "9000",
            },
        ),
        "wrong config type rejected",
    )

    expect_error(
        ValueError,
        lambda: worker.add_layer(
            "bad-range",
            1,
            values={
                "port": 70000,
            },
        ),
        "numeric maximum enforced",
    )

    expect_error(
        ValueError,
        lambda: worker.add_layer(
            "bad-choice",
            1,
            values={
                "environment": "staging",
            },
        ),
        "choice constraint enforced",
    )

    expect_error(
        ValueError,
        lambda: worker.add_layer(
            "unknown",
            1,
            values={
                "does_not_exist": True,
            },
        ),
        "unknown config key rejected",
    )


def test_transactional_required_removal():
    custom = ConfigSchema(
        "required-test"
    )

    custom.add_field(
        ConfigField(
            "required_value",
            "str",
            required=True,
        )
    )

    worker = ConfigManager(
        schema=custom
    )

    worker.add_layer(
        "base",
        1,
        values={
            "required_value": "present",
        },
    )

    expect_error(
        ValueError,
        lambda: worker.remove_layer(
            "base"
        ),
        "removing only required value rejected",
    )

    eq(
        worker.get_internal(
            "required_value"
        ),
        "present",
        "failed remove rolls back layer",
    )


def test_set_unset_and_version():
    worker = manager()

    worker.add_layer(
        "runtime",
        100,
    )

    version_after_add = (
        worker.version
    )

    worker.set_value(
        "runtime",
        "port",
        9999,
    )

    eq(
        worker.get_internal(
            "port"
        ),
        9999,
        "set_value updates resolved config",
    )

    eq(
        worker.version,
        version_after_add + 1,
        "set increments config version",
    )

    removed = worker.unset_value(
        "runtime",
        "port",
    )

    eq(
        removed,
        True,
        "unset reports removal",
    )

    eq(
        worker.get_internal(
            "port"
        ),
        8000,
        "unset falls back to schema default",
    )


def test_secret_redaction():
    worker = manager()

    worker.add_layer(
        "secret",
        100,
        values={
            "server_secret": (
                "very-secret-value"
            ),
        },
    )

    eq(
        worker.get_internal(
            "server_secret"
        ),
        "very-secret-value",
        "internal config retains secret",
    )

    public = worker.resolve_public()

    eq(
        public[
            "server_secret"
        ],
        "[REDACTED]",
        "public resolved config redacts secret",
    )

    public_item = worker.public_get(
        "server_secret"
    )

    eq(
        public_item[
            "value"
        ],
        "[REDACTED]",
        "public get redacts secret",
    )

    layer_text = repr(
        worker.list_layers()
    )

    check(
        "very-secret-value"
        not in layer_text,
        "layer listing does not leak secret",
    )

    schema_text = repr(
        worker.schema.public_dict()
    )

    check(
        "very-secret-value"
        not in schema_text,
        "public schema does not leak secret",
    )


def test_mutable_copy_isolation():
    worker = manager()

    features = [
        "rag",
    ]

    worker.add_layer(
        "runtime",
        1,
        values={
            "features": features,
        },
    )

    features.append(
        "external-change"
    )

    eq(
        worker.get_internal(
            "features"
        ),
        [
            "rag",
        ],
        "layer copies mutable input",
    )

    returned = worker.get_internal(
        "features"
    )

    returned.append(
        "caller-change"
    )

    eq(
        worker.get_internal(
            "features"
        ),
        [
            "rag",
        ],
        "resolved mutable value isolated from caller",
    )


def test_list_layers_order():
    worker = manager()

    worker.add_layer(
        "high",
        100,
    )

    worker.add_layer(
        "low",
        10,
    )

    worker.add_layer(
        "middle",
        50,
    )

    eq(
        [
            item[
                "layer_id"
            ]
            for item
            in worker.list_layers()
        ],
        [
            "low",
            "middle",
            "high",
        ],
        "layer list sorted by resolution order",
    )


def test_status():
    worker = manager()

    worker.add_layer(
        "runtime",
        100,
        values={
            "port": 9000,
        },
    )

    status = worker.status()

    eq(
        status[
            "ready"
        ],
        True,
        "config manager ready",
    )

    eq(
        status[
            "schema_id"
        ],
        "test-schema",
        "status schema ID",
    )

    eq(
        status[
            "layer_count"
        ],
        1,
        "status layer count",
    )

    eq(
        status[
            "secret_field_count"
        ],
        1,
        "status secret field count",
    )


def test_persistence_round_trip():
    if os.path.exists(
        STATE_PATH
    ):
        os.remove(
            STATE_PATH
        )

    source = manager()

    source.add_layer(
        "file",
        10,
        values={
            "port": 9000,
            "features": [
                "rag",
                "auth",
            ],
        },
    )

    source.add_layer(
        "runtime",
        100,
        values={
            "server_secret": (
                "persistent-secret"
            ),
            "debug": True,
        },
    )

    before = source.export_state(
        include_secrets=True
    )

    saved = source.save_state(
        STATE_PATH
    )

    check(
        saved[
            "bytes"
        ] > 0,
        "config state written",
    )

    restored = ConfigManager()

    restored.load_state_file(
        STATE_PATH
    )

    eq(
        restored.export_state(
            include_secrets=True
        ),
        before,
        "config state exact round trip",
    )

    eq(
        restored.get_internal(
            "server_secret"
        ),
        "persistent-secret",
        "internal persisted secret restored",
    )

    eq(
        restored.resolve_public()[
            "server_secret"
        ],
        "[REDACTED]",
        "restored public view still redacts secret",
    )


def test_persistence_corruption():
    source = manager()

    source.save_state(
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
        lambda: ConfigManager().load_state_file(
            STATE_PATH
        ),
        "config snapshot checksum detects corruption",
    )


def test_service_secret_safety():
    worker = manager()

    service = ConfigService(
        worker
    )

    added = service.handle(
        ServiceRequest(
            "s1",
            "config_service",
            "add_layer",
            payload={
                "layer_id": "runtime",
                "priority": 100,
                "values": {
                    "server_secret": (
                        "never-expose-this"
                    ),
                    "port": 9000,
                },
            },
        )
    )

    eq(
        added.success,
        True,
        "service add layer succeeds",
    )

    check(
        "never-expose-this"
        not in repr(
            added.data
        ),
        "add-layer response redacts secret",
    )

    resolved = service.handle(
        ServiceRequest(
            "s2",
            "config_service",
            "resolve",
        )
    )

    eq(
        resolved.data[
            "config"
        ][
            "server_secret"
        ],
        "[REDACTED]",
        "service resolve redacts secret",
    )

    fetched = service.handle(
        ServiceRequest(
            "s3",
            "config_service",
            "get",
            payload={
                "key": "server_secret",
            },
        )
    )

    check(
        "never-expose-this"
        not in repr(
            fetched.data
        ),
        "service get never exposes secret",
    )


def test_service_mutation():
    worker = manager()
    worker.add_layer(
        "runtime",
        100,
    )

    service = ConfigService(
        worker
    )

    changed = service.handle(
        ServiceRequest(
            "m1",
            "config_service",
            "set_value",
            payload={
                "layer_id": "runtime",
                "key": "port",
                "value": 9876,
            },
        )
    )

    eq(
        changed.success,
        True,
        "service config mutation succeeds",
    )

    eq(
        changed.data[
            "config"
        ][
            "value"
        ],
        9876,
        "service returns updated value",
    )

    validated = service.handle(
        ServiceRequest(
            "m2",
            "config_service",
            "validate",
        )
    )

    eq(
        validated.data[
            "valid"
        ],
        True,
        "service validates resolved config",
    )


def test_protocol_round_trip():
    worker = manager()
    worker.add_layer(
        "runtime",
        100,
        values={
            "port": 9001,
        },
    )

    service = ConfigService(
        worker
    )

    codec = ProtocolCodec()

    request = ServiceRequest(
        "protocol-config",
        "config_service",
        "get",
        payload={
            "key": "port",
        },
        trace_id="trace-config",
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
        "config get survives protocol codec",
    )

    eq(
        response.trace_id,
        "trace-config",
        "config trace preserved",
    )

    eq(
        response.data[
            "config"
        ][
            "value"
        ],
        9001,
        "protocol config value preserved",
    )


def test_default_builder():
    worker = (
        build_default_config_manager()
    )

    resolved = worker.resolve_internal()

    eq(
        resolved[
            "environment"
        ],
        "development",
        "default builder environment",
    )

    eq(
        resolved[
            "model_id"
        ],
        "sirellm",
        "default builder model ID",
    )

    eq(
        worker.schema.get(
            "auth_server_secret"
        ).secret,
        True,
        "default auth secret marked secret",
    )


def test_errors():
    service = ConfigService(
        manager()
    )

    missing = service.handle(
        ServiceRequest(
            "e1",
            "config_service",
            "get",
            payload={
                "key": "missing",
            },
        )
    )

    eq(
        missing.error.code,
        "NOT_FOUND",
        "missing config maps to NOT_FOUND",
    )

    invalid = service.handle(
        ServiceRequest(
            "e2",
            "config_service",
            "add_layer",
            payload={
                "layer_id": "bad",
                "priority": 1,
                "values": {
                    "port": -1,
                },
            },
        )
    )

    eq(
        invalid.error.code,
        "INVALID_REQUEST",
        "invalid config maps to INVALID_REQUEST",
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

    expect_error(
        TypeError,
        lambda: service.handle(
            {}
        ),
        "non-ServiceRequest rejected",
    )


def main():
    try:
        test_defaults()
        test_layer_precedence()
        test_same_priority_insertion_order()
        test_validation_types_constraints()
        test_transactional_required_removal()
        test_set_unset_and_version()
        test_secret_redaction()
        test_mutable_copy_isolation()
        test_list_layers_order()
        test_status()
        test_persistence_round_trip()
        test_persistence_corruption()
        test_service_secret_safety()
        test_service_mutation()
        test_protocol_round_trip()
        test_default_builder()
        test_errors()

    finally:
        if os.path.exists(
            STATE_PATH
        ):
            os.remove(
                STATE_PATH
            )

    print(
        "CONFIG SERVICE TEST SUITE: PASS"
    )
    print(
        "Assertions passed:",
        ASSERTIONS,
    )
    print(
        "Files validated: 5/5"
    )
    print(
        "Typed schema/default validation: VALIDATED"
    )
    print(
        "Deterministic layered precedence: VALIDATED"
    )
    print(
        "Transactional config mutations: VALIDATED"
    )
    print(
        "Secret redaction/public isolation: VALIDATED"
    )
    print(
        "Source-layer attribution/versioning: VALIDATED"
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
