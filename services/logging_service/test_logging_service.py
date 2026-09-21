import os

SERIAL_BASE = "libs/core/serialization/"
PROTOCOL_BASE = "libs/protocol/"
SERVICE_BASE = "services/logging_service/"

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
    "record.py",
    "sanitizer.py",
    "sink.py",
    "archive.py",
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
            "logging_service implementation contains forbidden import: "
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

ARCHIVE_PATH = (
    "services/logging_service/"
    "_test_logs.sllog"
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


def test_record_validation():
    record = LogRecord(
        sequence=1,
        level="info",
        message="started",
        timestamp=100,
        service="rag_service",
        event="startup",
        fields={
            "ok": True,
        },
    )

    eq(
        record.level,
        "INFO",
        "log level normalized",
    )

    eq(
        record.rank(),
        20,
        "INFO rank",
    )

    restored = LogRecord.from_dict(
        record.to_dict()
    )

    eq(
        restored.to_dict(),
        record.to_dict(),
        "log record state round trip",
    )


def test_minimum_level():
    manager = LoggingManager(
        minimum_level="INFO"
    )

    skipped = manager.debug(
        "debug",
        1,
    )

    accepted = manager.info(
        "info",
        2,
    )

    eq(
        skipped[
            "accepted"
        ],
        False,
        "below-minimum log filtered",
    )

    eq(
        accepted[
            "accepted"
        ],
        True,
        "minimum-level log accepted",
    )

    eq(
        manager.status()[
            "filtered_records"
        ],
        1,
        "filtered log counted",
    )


def test_sequence_and_levels():
    manager = LoggingManager()

    manager.debug(
        "d",
        1,
    )
    manager.info(
        "i",
        2,
    )
    manager.warning(
        "w",
        3,
    )
    manager.error(
        "e",
        4,
    )
    manager.critical(
        "c",
        5,
    )

    records = manager.query(
        limit=10
    )[
        "records"
    ]

    eq(
        [
            row[
                "sequence"
            ]
            for row in records
        ],
        [
            1,
            2,
            3,
            4,
            5,
        ],
        "log sequence deterministic",
    )

    eq(
        [
            row[
                "level"
            ]
            for row in records
        ],
        [
            "DEBUG",
            "INFO",
            "WARNING",
            "ERROR",
            "CRITICAL",
        ],
        "all log levels preserved",
    )


def test_structured_redaction():
    manager = LoggingManager()

    result = manager.info(
        "login completed",
        1,
        service="auth_service",
        fields={
            "user_id": "u1",
            "password": "NeverLogThis",
            "nested": {
                "api_key": "abc123",
                "safe": "ok",
            },
        },
    )

    record = result[
        "record"
    ]

    eq(
        record[
            "fields"
        ][
            "password"
        ],
        "[REDACTED]",
        "password field redacted",
    )

    eq(
        record[
            "fields"
        ][
            "nested"
        ][
            "api_key"
        ],
        "[REDACTED]",
        "nested API key redacted",
    )

    eq(
        record[
            "fields"
        ][
            "nested"
        ][
            "safe"
        ],
        "ok",
        "safe field preserved",
    )

    check(
        "NeverLogThis"
        not in repr(
            record
        ),
        "plaintext password absent from structured log",
    )


def test_inline_redaction():
    sanitizer = LogSanitizer()

    message = (
        "request token=abc123 user=u1 "
        "api_key=secret987 done"
    )

    sanitized = (
        sanitizer
        .sanitize_message(
            message
        )
    )

    check(
        "abc123"
        not in sanitized,
        "inline token value redacted",
    )

    check(
        "secret987"
        not in sanitized,
        "inline API key value redacted",
    )

    check(
        "[REDACTED]"
        in sanitized,
        "redaction marker inserted",
    )


def test_trace_and_correlation():
    manager = LoggingManager()

    manager.info(
        "request",
        1,
        trace_id="trace-1",
        correlation_id="req-1",
    )

    result = manager.query(
        trace_id="trace-1",
        correlation_id="req-1",
    )

    eq(
        result[
            "count"
        ],
        1,
        "trace/correlation query",
    )


def test_query_filters():
    manager = LoggingManager()

    manager.info(
        "a",
        10,
        service="rag_service",
        event="request",
    )
    manager.error(
        "b",
        20,
        service="rag_service",
        event="request",
    )
    manager.warning(
        "c",
        30,
        service="auth_service",
        event="security",
    )
    manager.critical(
        "d",
        40,
        service="auth_service",
        event="security",
    )

    errors = manager.query(
        minimum_level="ERROR",
        limit=10,
    )

    eq(
        [
            item[
                "level"
            ]
            for item in errors[
                "records"
            ]
        ],
        [
            "ERROR",
            "CRITICAL",
        ],
        "minimum-level query filter",
    )

    auth = manager.query(
        service="auth_service",
        event="security",
        start_timestamp=25,
        end_timestamp=40,
    )

    eq(
        auth[
            "count"
        ],
        2,
        "service/event/time query filters",
    )

    newest = manager.query(
        limit=2,
        newest_first=True,
    )

    eq(
        [
            item[
                "message"
            ]
            for item in newest[
                "records"
            ]
        ],
        [
            "d",
            "c",
        ],
        "newest-first query",
    )


def test_bounded_sink_eviction():
    manager = LoggingManager(
        max_records=3
    )

    manager.info(
        "one",
        1,
    )
    manager.info(
        "two",
        2,
    )
    manager.info(
        "three",
        3,
    )
    manager.info(
        "four",
        4,
    )

    records = manager.query(
        limit=10
    )[
        "records"
    ]

    eq(
        [
            row[
                "message"
            ]
            for row in records
        ],
        [
            "two",
            "three",
            "four",
        ],
        "oldest record evicted when sink full",
    )

    eq(
        manager.status()[
            "evicted_records"
        ],
        1,
        "sink eviction counted",
    )


def test_status_counts():
    manager = LoggingManager()

    manager.info(
        "i1",
        1,
    )
    manager.info(
        "i2",
        2,
    )
    manager.error(
        "e1",
        3,
    )

    status = manager.status()

    eq(
        status[
            "retained_records"
        ],
        3,
        "status retained count",
    )

    eq(
        status[
            "counts_by_level"
        ][
            "INFO"
        ],
        2,
        "INFO status count",
    )

    eq(
        status[
            "counts_by_level"
        ][
            "ERROR"
        ],
        1,
        "ERROR status count",
    )


def test_clear():
    manager = LoggingManager()

    manager.info(
        "a",
        1,
    )
    manager.info(
        "b",
        2,
    )

    cleared = manager.clear()

    eq(
        cleared[
            "cleared_records"
        ],
        2,
        "clear reports removed records",
    )

    eq(
        manager.status()[
            "retained_records"
        ],
        0,
        "no records after clear",
    )


def test_archive_round_trip():
    if os.path.exists(
        ARCHIVE_PATH
    ):
        os.remove(
            ARCHIVE_PATH
        )

    manager = LoggingManager()

    manager.info(
        "start",
        100,
        service="rag_service",
        trace_id="t1",
        fields={
            "count": 1,
        },
    )

    manager.error(
        "failed",
        101,
        service="retrieval_service",
        correlation_id="r2",
        fields={
            "code": "X",
        },
    )

    before = manager.query(
        limit=10
    )[
        "records"
    ]

    saved = manager.save_archive(
        ARCHIVE_PATH
    )

    eq(
        saved[
            "records"
        ],
        2,
        "archive record count",
    )

    restored = LoggingManager()

    loaded = restored.load_archive(
        ARCHIVE_PATH
    )

    eq(
        loaded[
            "loaded_records"
        ],
        2,
        "archive load count",
    )

    after = restored.query(
        limit=10
    )[
        "records"
    ]

    eq(
        after,
        before,
        "archive exact record round trip",
    )

    next_record = restored.info(
        "next",
        102,
    )[
        "record"
    ]

    eq(
        next_record[
            "sequence"
        ],
        3,
        "sequence resumes after archive load",
    )


def test_archive_corruption():
    manager = LoggingManager()

    manager.info(
        "x",
        1,
    )

    manager.save_archive(
        ARCHIVE_PATH
    )

    handle = open(
        ARCHIVE_PATH,
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
        ARCHIVE_PATH,
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
        lambda: LoggingManager().load_archive(
            ARCHIVE_PATH
        ),
        "archive checksum detects corruption",
    )


def test_service_logging():
    service = LoggingService()

    response = service.handle(
        ServiceRequest(
            "log-1",
            "logging_service",
            "info",
            payload={
                "message": (
                    "request processed"
                ),
                "timestamp": 100,
                "service": (
                    "rag_service"
                ),
                "event": "request",
                "fields": {
                    "token": "do-not-log",
                    "status": 200,
                },
            },
            trace_id="trace-service",
            correlation_id=(
                "correlation-service"
            ),
        )
    )

    eq(
        response.success,
        True,
        "logging service accepts record",
    )

    record = response.data[
        "log"
    ][
        "record"
    ]

    eq(
        record[
            "trace_id"
        ],
        "trace-service",
        "request trace becomes log trace",
    )

    eq(
        record[
            "correlation_id"
        ],
        "correlation-service",
        "request correlation becomes log correlation",
    )

    eq(
        record[
            "fields"
        ][
            "token"
        ],
        "[REDACTED]",
        "service log fields sanitized",
    )


def test_service_query_and_level():
    service = LoggingService()

    service.handle(
        ServiceRequest(
            "a",
            "logging_service",
            "info",
            payload={
                "message": "one",
                "timestamp": 1,
            },
        )
    )

    service.handle(
        ServiceRequest(
            "b",
            "logging_service",
            "error",
            payload={
                "message": "two",
                "timestamp": 2,
            },
        )
    )

    query = service.handle(
        ServiceRequest(
            "q",
            "logging_service",
            "query",
            payload={
                "minimum_level": (
                    "ERROR"
                ),
            },
        )
    )

    eq(
        query.data[
            "query"
        ][
            "count"
        ],
        1,
        "service query filters",
    )

    changed = service.handle(
        ServiceRequest(
            "l",
            "logging_service",
            "set_minimum_level",
            payload={
                "level": "WARNING",
            },
        )
    )

    eq(
        changed.data[
            "minimum_level"
        ],
        "WARNING",
        "service minimum level updated",
    )


def test_protocol_round_trip():
    service = LoggingService()
    codec = ProtocolCodec()

    request = ServiceRequest(
        "protocol-log",
        "logging_service",
        "warning",
        payload={
            "message": "warning event",
            "timestamp": 50,
            "service": "auth_service",
            "fields": {
                "reason": "test",
            },
        },
        trace_id="trace-log",
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
        "logging survives protocol codec",
    )

    eq(
        response.trace_id,
        "trace-log",
        "logging trace preserved",
    )

    eq(
        response.data[
            "log"
        ][
            "record"
        ][
            "level"
        ],
        "WARNING",
        "protocol log level preserved",
    )


def test_service_archive():
    if os.path.exists(
        ARCHIVE_PATH
    ):
        os.remove(
            ARCHIVE_PATH
        )

    source = LoggingService()

    source.handle(
        ServiceRequest(
            "a",
            "logging_service",
            "info",
            payload={
                "message": "persist",
                "timestamp": 1,
            },
        )
    )

    saved = source.handle(
        ServiceRequest(
            "b",
            "logging_service",
            "save_archive",
            payload={
                "path": ARCHIVE_PATH,
            },
        )
    )

    eq(
        saved.success,
        True,
        "service saves log archive",
    )

    target = LoggingService()

    loaded = target.handle(
        ServiceRequest(
            "c",
            "logging_service",
            "load_archive",
            payload={
                "path": ARCHIVE_PATH,
            },
        )
    )

    eq(
        loaded.success,
        True,
        "service loads log archive",
    )

    status = target.handle(
        ServiceRequest(
            "d",
            "logging_service",
            "status",
        )
    )

    eq(
        status.data[
            "status"
        ][
            "retained_records"
        ],
        1,
        "loaded archive reflected in status",
    )


def test_errors():
    service = LoggingService()

    invalid_level = service.handle(
        ServiceRequest(
            "e1",
            "logging_service",
            "log",
            payload={
                "level": "NOPE",
                "message": "x",
                "timestamp": 1,
            },
        )
    )

    eq(
        invalid_level.error.code,
        "INVALID_REQUEST",
        "invalid level rejected",
    )

    missing = service.handle(
        ServiceRequest(
            "e2",
            "logging_service",
            "info",
            payload={
                "timestamp": 1,
            },
        )
    )

    eq(
        missing.error.code,
        "INVALID_REQUEST",
        "missing message rejected",
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


def test_validation():
    expect_error(
        ValueError,
        lambda: LoggingManager(
            minimum_level="NOPE"
        ),
        "invalid manager minimum level rejected",
    )

    expect_error(
        ValueError,
        lambda: MemoryLogSink(
            max_records=0
        ),
        "invalid sink capacity rejected",
    )

    expect_error(
        ValueError,
        lambda: LogRecord(
            0,
            "INFO",
            "x",
            1,
        ),
        "invalid sequence rejected",
    )


def main():
    try:
        test_record_validation()
        test_minimum_level()
        test_sequence_and_levels()
        test_structured_redaction()
        test_inline_redaction()
        test_trace_and_correlation()
        test_query_filters()
        test_bounded_sink_eviction()
        test_status_counts()
        test_clear()
        test_archive_round_trip()
        test_archive_corruption()
        test_service_logging()
        test_service_query_and_level()
        test_protocol_round_trip()
        test_service_archive()
        test_errors()
        test_validation()

    finally:
        if os.path.exists(
            ARCHIVE_PATH
        ):
            os.remove(
                ARCHIVE_PATH
            )

    print(
        "LOGGING SERVICE TEST SUITE: PASS"
    )
    print(
        "Assertions passed:",
        ASSERTIONS,
    )
    print(
        "Files validated: 6/6"
    )
    print(
        "Structured deterministic log records: VALIDATED"
    )
    print(
        "Level filtering/querying: VALIDATED"
    )
    print(
        "Trace/correlation propagation: VALIDATED"
    )
    print(
        "Sensitive-field/message redaction: VALIDATED"
    )
    print(
        "Bounded retention/eviction: VALIDATED"
    )
    print(
        "Checksum-protected binary archive: VALIDATED"
    )
    print(
        "Protocol service operations: VALIDATED"
    )
    print(
        "Third-party dependencies: 0"
    )


main()
