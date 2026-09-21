import os

SERIAL_BASE = "libs/core/serialization/"
PARSER_BASE = "libs/data/parsers/"
PROTOCOL_BASE = "libs/protocol/"
SERVICE_BASE = "services/config_service/"
CONFIG_BASE = "configs/config_service/"

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
        SERVICE_BASE,
        [
            "layer.py",
            "persistence.py",
            "schema.py",
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
    "field.py",
    "layer.py",
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
            "config-service config implementation contains forbidden import: "
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

globals().update(namespace)

ASSERTIONS = 0
STATE_PATH = (
    "configs/config_service/"
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
    load=False,
):
    return ConfigServiceConfig(
        schema_id="test-runtime",
        fields=[
            RuntimeConfigFieldConfig(
                key="environment",
                value_type="str",
                required=True,
                default="development",
                choices=[
                    "development",
                    "production",
                ],
            ),
            RuntimeConfigFieldConfig(
                key="port",
                value_type="int",
                required=True,
                default=8000,
                minimum=1,
                maximum=65535,
            ),
            RuntimeConfigFieldConfig(
                key="debug",
                value_type="bool",
                required=True,
                default=False,
            ),
            RuntimeConfigFieldConfig(
                key="features",
                value_type="list",
                default=[],
            ),
            RuntimeConfigFieldConfig(
                key="routing",
                value_type="dict",
                default={},
            ),
            RuntimeConfigFieldConfig(
                key="server_secret",
                value_type="str",
                required=False,
                default=None,
                secret=True,
            ),
        ],
        layers=[
            RuntimeConfigLayerConfig(
                layer_id="base",
                priority=10,
                values={
                    "port": 8100,
                    "features": [
                        "rag",
                    ],
                },
            ),
            RuntimeConfigLayerConfig(
                layer_id="production",
                priority=20,
                values={
                    "environment": (
                        "production"
                    ),
                    "port": 9000,
                    "server_secret": (
                        "super-secret"
                    ),
                },
            ),
            RuntimeConfigLayerConfig(
                layer_id="disabled",
                priority=999,
                values={
                    "port": 1,
                },
                enabled=False,
            ),
        ],
        state_path=STATE_PATH,
        load_state_on_start=load,
    )


def test_field_config():
    field = RuntimeConfigFieldConfig(
        "port",
        "int",
        required=True,
        default=8000,
        minimum=1,
        maximum=65535,
    )

    runtime = (
        field.to_runtime_field()
    )

    eq(
        runtime.key,
        "port",
        "typed config field maps to runtime field",
    )

    eq(
        runtime.default,
        8000,
        "field default preserved",
    )

    expect_error(
        ValueError,
        lambda: (
            RuntimeConfigFieldConfig(
                "port",
                "int",
                default=0,
                minimum=1,
            )
        ),
        "runtime field constraints validated at config creation",
    )


def test_defaults():
    config = (
        default_config_service_config()
    )

    eq(
        config.schema_id,
        "sirellm-runtime",
        "default config schema ID",
    )

    eq(
        len(
            config.fields
        ),
        5,
        "default runtime config contains five core fields",
    )

    secret = [
        field
        for field in config.fields
        if field.key
        == "auth_server_secret"
    ][0]

    eq(
        secret.secret,
        True,
        "default auth secret marked secret",
    )


def test_codec():
    text = (
        '{"schema_id":"runtime",'
        '"fields":['
        '{"key":"port",'
        '"value_type":"int",'
        '"required":true,'
        '"default":8000,'
        '"minimum":1,'
        '"maximum":65535},'
        '{"key":"secret",'
        '"value_type":"str",'
        '"secret":true}'
        '],'
        '"layers":['
        '{"layer_id":"env",'
        '"priority":10,'
        '"values":{"port":9000},'
        '"enabled":true}'
        '],'
        '"state_path":"state/config.bin",'
        '"load_state_on_start":false,'
        '"metadata":{"profile":"prod"}'
        '}'
    )

    config = (
        ConfigServiceConfigCodec()
        .decode_text(
            text
        )
    )

    eq(
        config.schema_id,
        "runtime",
        "codec schema ID",
    )

    eq(
        config.fields[
            1
        ].secret,
        True,
        "codec secret field",
    )

    eq(
        config.layers[
            0
        ].values[
            "port"
        ],
        9000,
        "codec layer values",
    )


def test_validator():
    config = ConfigServiceConfig(
        schema_id="runtime",
        fields=[
            RuntimeConfigFieldConfig(
                "port",
                "int",
                default=8000,
            ),
        ],
        layers=[
            RuntimeConfigLayerConfig(
                "bad",
                10,
                values={
                    "missing": 1,
                },
            ),
        ],
    )

    result = (
        ConfigServiceConfigValidator()
        .validate(
            config
        )
    )

    eq(
        result[
            "valid"
        ],
        False,
        "unknown layered key rejected",
    )

    eq(
        result[
            "errors"
        ][0][
            "code"
        ],
        "UNKNOWN_CONFIG_LAYER_KEY",
        "unknown layer key validation code",
    )


def test_manager_resolution():
    manager = (
        ConfigServiceConfigFactory()
        .build_manager(
            sample_config()
        )
    )

    resolved = (
        manager.resolve_internal()
    )

    eq(
        resolved[
            "environment"
        ],
        "production",
        "higher-priority environment layer wins",
    )

    eq(
        resolved[
            "port"
        ],
        9000,
        "higher-priority port override wins",
    )

    eq(
        resolved[
            "debug"
        ],
        False,
        "schema default survives when not overridden",
    )

    eq(
        manager.source_layer(
            "port"
        ),
        "production",
        "resolved source layer exposed",
    )

    eq(
        manager.status()[
            "layer_count"
        ],
        2,
        "disabled config layer excluded",
    )


def test_secret_redaction():
    manager = (
        ConfigServiceConfigFactory()
        .build_manager(
            sample_config()
        )
    )

    eq(
        manager.get_internal(
            "server_secret"
        ),
        "super-secret",
        "internal manager retains secret",
    )

    public = manager.public_get(
        "server_secret"
    )

    eq(
        public["value"],
        "[REDACTED]",
        "public config lookup redacts secret",
    )

    layers = manager.list_layers()

    eq(
        layers[1][
            "values"
        ][
            "server_secret"
        ],
        "[REDACTED]",
        "public layer listing redacts secret",
    )


def test_runtime_mutation():
    manager = (
        ConfigServiceConfigFactory()
        .build_manager(
            sample_config()
        )
    )

    initial_version = (
        manager.version
    )

    result = manager.set_value(
        "production",
        "port",
        9100,
    )

    eq(
        result["value"],
        9100,
        "runtime layer mutation succeeds",
    )

    eq(
        manager.version,
        initial_version + 1,
        "runtime config version increments",
    )

    expect_error(
        ValueError,
        lambda: manager.set_value(
            "production",
            "port",
            70000,
        ),
        "runtime mutation respects schema constraints",
    )

    eq(
        manager.get_internal(
            "port"
        ),
        9100,
        "failed mutation rolls back transactionally",
    )


def test_persistence_round_trip():
    cleanup()

    manager = (
        ConfigServiceConfigFactory()
        .build_manager(
            sample_config()
        )
    )

    artifact = (
        ConfigServiceConfigFactory()
        .save_state(
            manager,
            sample_config(),
        )
    )

    check(
        artifact[
            "bytes"
        ] > 0,
        "config snapshot persisted",
    )

    loaded = (
        ConfigServiceConfigFactory()
        .build_manager(
            sample_config(
                load=True
            )
        )
    )

    eq(
        loaded.export_state(
            include_secrets=True
        ),
        manager.export_state(
            include_secrets=True
        ),
        "configured startup load restores exact internal state",
    )

    eq(
        loaded.public_get(
            "server_secret"
        )[
            "value"
        ],
        "[REDACTED]",
        "secret remains redacted after state reload",
    )


def test_corruption_boundary():
    cleanup()

    manager = (
        ConfigServiceConfigFactory()
        .build_manager(
            sample_config()
        )
    )

    ConfigServiceConfigFactory().save_state(
        manager,
        sample_config(),
    )

    raw = open(
        STATE_PATH,
        "rb",
    ).read()

    damaged = bytearray(
        raw
    )
    damaged[-1] ^= 1

    open(
        STATE_PATH,
        "wb",
    ).write(
        bytes(
            damaged
        )
    )

    expect_error(
        ValueError,
        lambda: (
            ConfigServiceConfigFactory()
            .build_manager(
                sample_config(
                    load=True
                )
            )
        ),
        "corrupted config snapshot rejected",
    )


def test_service_creation():
    service = (
        ConfigServiceConfigFactory()
        .build_service(
            sample_config()
        )
    )

    check(
        isinstance(
            service,
            ConfigService,
        ),
        "factory creates ConfigService",
    )

    get_secret = service.handle(
        ServiceRequest(
            "cfg-secret",
            "config_service",
            "get",
            payload={
                "key": (
                    "server_secret"
                ),
            },
        )
    )

    eq(
        get_secret.success,
        True,
        "configured config service resolves field",
    )

    eq(
        get_secret.data[
            "config"
        ][
            "value"
        ],
        "[REDACTED]",
        "service never exposes configured secret",
    )

    set_port = service.handle(
        ServiceRequest(
            "cfg-set",
            "config_service",
            "set_value",
            payload={
                "layer_id": (
                    "production"
                ),
                "key": "port",
                "value": 9200,
            },
        )
    )

    eq(
        set_port.success,
        True,
        "configured config service mutates layer",
    )

    resolve = service.handle(
        ServiceRequest(
            "cfg-resolve",
            "config_service",
            "resolve",
        )
    )

    eq(
        resolve.data[
            "config"
        ][
            "port"
        ],
        9200,
        "protocol resolve sees updated layered value",
    )

    eq(
        resolve.data[
            "config"
        ][
            "server_secret"
        ],
        "[REDACTED]",
        "protocol resolve redacts secret",
    )


def test_default_runtime_parity():
    config = (
        default_config_service_config()
    )

    configured = (
        ConfigServiceConfigFactory()
        .build_manager(
            config
        )
    )

    builtin = (
        build_default_config_manager()
    )

    eq(
        configured.resolve_internal()[
            "environment"
        ],
        builtin.resolve_internal()[
            "environment"
        ],
        "typed default config matches runtime builder environment",
    )

    eq(
        configured.resolve_internal()[
            "model_id"
        ],
        builtin.resolve_internal()[
            "model_id"
        ],
        "typed default config matches runtime builder model ID",
    )

    eq(
        configured.schema.get(
            "auth_server_secret"
        ).secret,
        builtin.schema.get(
            "auth_server_secret"
        ).secret,
        "typed default config preserves runtime secret classification",
    )


def main():
    cleanup()

    try:
        test_field_config()
        test_defaults()
        test_codec()
        test_validator()
        test_manager_resolution()
        test_secret_redaction()
        test_runtime_mutation()
        test_persistence_round_trip()
        test_corruption_boundary()
        test_service_creation()
        test_default_runtime_parity()

    finally:
        cleanup()

    print(
        "CONFIG SERVICE CONFIG TEST SUITE: PASS"
    )
    print(
        "Assertions passed:",
        ASSERTIONS,
    )
    print(
        "Files validated: 7/7"
    )
    print(
        "Typed schema/layer configuration: VALIDATED"
    )
    print(
        "Handwritten JSON decoding: VALIDATED"
    )
    print(
        "Layer precedence/source tracking: VALIDATED"
    )
    print(
        "Secret redaction boundary: VALIDATED"
    )
    print(
        "Transactional runtime mutation: VALIDATED"
    )
    print(
        "Binary snapshot/checksum restore: VALIDATED"
    )
    print(
        "Built-in runtime default parity: VALIDATED"
    )
    print(
        "ConfigService generation: VALIDATED"
    )
    print(
        "Third-party dependencies: 0"
    )


main()
