PARSERS_BASE = "libs/data/parsers/"
LOGGING_BASE = "services/logging_service/"
CONFIG_BASE = "configs/logging/"

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
        LOGGING_BASE,
        [
            "record.py",
            "sanitizer.py",
            "sink.py",
            "archive.py",
            "manager.py",
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
    "sink.py",
    "config.py",
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
            "logging config implementation contains forbidden import: "
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


def test_sink_config():
    sink = LogSinkConfig(
        "memory",
        max_records=500,
        metadata={
            "purpose": "runtime",
        },
    )

    eq(
        sink.max_records,
        500,
        "log sink capacity",
    )

    eq(
        sink.to_dict()[
            "metadata"
        ][
            "purpose"
        ],
        "runtime",
        "log sink metadata",
    )


def test_codec():
    text = (
        '{"minimum_level":"warning",'
        '"sinks":['
        '{"sink_id":"memory","max_records":200,"enabled":true}'
        '],'
        '"archive_path":"logs/runtime.bin"}'
    )

    config = (
        LoggingConfigCodec()
        .decode_text(
            text
        )
    )

    eq(
        config.minimum_level,
        "WARNING",
        "codec normalizes minimum log level",
    )

    eq(
        config.sinks[
            0
        ].max_records,
        200,
        "codec maps sink capacity",
    )

    eq(
        config.archive_path,
        "logs/runtime.bin",
        "codec maps archive path",
    )


def test_validator_valid():
    config = LoggingConfig(
        minimum_level="INFO",
        sinks=[
            LogSinkConfig(
                "memory",
                100,
            ),
        ],
    )

    result = (
        LoggingConfigValidator()
        .validate(
            config
        )
    )

    eq(
        result[
            "valid"
        ],
        True,
        "single enabled logging sink valid",
    )

    eq(
        result[
            "enabled_sink_count"
        ],
        1,
        "validator enabled sink count",
    )


def test_validator_no_enabled_sink():
    config = LoggingConfig(
        sinks=[
            LogSinkConfig(
                "memory",
                enabled=False,
            ),
        ],
    )

    result = (
        LoggingConfigValidator()
        .validate(
            config
        )
    )

    eq(
        result[
            "valid"
        ],
        False,
        "no enabled log sink invalid",
    )

    eq(
        result[
            "errors"
        ][
            0
        ][
            "code"
        ],
        "NO_ENABLED_LOG_SINK",
        "no enabled sink error code",
    )


def test_multiple_enabled_sink_rejected():
    config = LoggingConfig(
        sinks=[
            LogSinkConfig(
                "one",
            ),
            LogSinkConfig(
                "two",
            ),
        ],
    )

    result = (
        LoggingConfigValidator()
        .validate(
            config
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
        "MULTIPLE_ENABLED_LOG_SINKS"
        in codes,
        "multiple enabled sinks rejected for current runtime manager",
    )


def test_debug_warning():
    config = LoggingConfig(
        minimum_level="DEBUG",
        sinks=[
            LogSinkConfig(
                "memory",
            ),
        ],
    )

    result = (
        LoggingConfigValidator()
        .validate(
            config
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
        "DEBUG_LOGGING_ENABLED"
        in codes,
        "debug logging warning emitted",
    )


def test_factory_manager():
    config = LoggingConfig(
        minimum_level="WARNING",
        sinks=[
            LogSinkConfig(
                "memory",
                max_records=2,
            ),
        ],
    )

    manager = (
        LoggingConfigFactory()
        .build_manager(
            config
        )
    )

    eq(
        manager.status()[
            "minimum_level"
        ],
        "WARNING",
        "factory applies minimum log level",
    )

    eq(
        manager.status()[
            "max_records"
        ],
        2,
        "factory applies sink capacity",
    )

    filtered = manager.info(
        "not retained",
        timestamp=1,
    )

    eq(
        filtered[
            "accepted"
        ],
        False,
        "below-minimum log filtered",
    )

    accepted = manager.warning(
        "warning token=secret-value",
        timestamp=2,
        fields={
            "password": "hidden",
            "safe": "visible",
        },
    )

    eq(
        accepted[
            "accepted"
        ],
        True,
        "configured warning retained",
    )

    record = manager.query(
        limit=10
    )[
        "records"
    ][
        0
    ]

    check(
        "secret-value"
        not in record[
            "message"
        ],
        "configured manager sanitizes inline token",
    )

    eq(
        record[
            "fields"
        ][
            "password"
        ],
        "[REDACTED]",
        "configured manager sanitizes sensitive structured field",
    )

    eq(
        record[
            "fields"
        ][
            "safe"
        ],
        "visible",
        "configured manager preserves safe structured field",
    )


def test_retention_capacity():
    config = LoggingConfig(
        minimum_level="DEBUG",
        sinks=[
            LogSinkConfig(
                "memory",
                max_records=2,
            ),
        ],
    )

    manager = (
        LoggingConfigFactory()
        .build_manager(
            config
        )
    )

    manager.info(
        "one",
        timestamp=1,
    )

    manager.info(
        "two",
        timestamp=2,
    )

    manager.info(
        "three",
        timestamp=3,
    )

    status = manager.status()

    eq(
        status[
            "retained_records"
        ],
        2,
        "configured log retention capacity enforced",
    )

    eq(
        status[
            "evicted_records"
        ],
        1,
        "configured log eviction counted",
    )

    records = manager.query(
        limit=10
    )[
        "records"
    ]

    eq(
        records[
            0
        ][
            "message"
        ],
        "two",
        "oldest log evicted",
    )


def test_archive_path_boundary():
    config = LoggingConfig(
        sinks=[
            LogSinkConfig(
                "memory",
            ),
        ],
        archive_path=(
            "logs/runtime.bin"
        ),
    )

    eq(
        LoggingConfigFactory()
        .archive_path(
            config
        ),
        "logs/runtime.bin",
        "factory exposes configured archive path without filesystem side effect",
    )


def test_duplicate_sink_rejected():
    expect_error(
        ValueError,
        lambda: LoggingConfig(
            sinks=[
                LogSinkConfig(
                    "same"
                ),
                LogSinkConfig(
                    "same"
                ),
            ],
        ),
        "duplicate sink id rejected",
    )


def main():
    test_sink_config()
    test_codec()
    test_validator_valid()
    test_validator_no_enabled_sink()
    test_multiple_enabled_sink_rejected()
    test_debug_warning()
    test_factory_manager()
    test_retention_capacity()
    test_archive_path_boundary()
    test_duplicate_sink_rejected()

    print(
        "LOGGING CONFIG TEST SUITE: PASS"
    )
    print(
        "Assertions passed:",
        ASSERTIONS,
    )
    print(
        "Files validated: 5/5"
    )
    print(
        "Typed logging/sink configuration: VALIDATED"
    )
    print(
        "Handwritten JSON decoding: VALIDATED"
    )
    print(
        "Single runtime sink constraint: VALIDATED"
    )
    print(
        "LoggingManager generation: VALIDATED"
    )
    print(
        "Minimum-level filtering: VALIDATED"
    )
    print(
        "Bounded retention/eviction: VALIDATED"
    )
    print(
        "Sensitive log sanitization: VALIDATED"
    )
    print(
        "Archive-path configuration boundary: VALIDATED"
    )
    print(
        "Third-party dependencies: 0"
    )


main()
