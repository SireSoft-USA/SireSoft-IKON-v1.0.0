import os

SERIAL_BASE = "libs/core/serialization/"
PROTOCOL_BASE = "libs/protocol/"
SERVICE_BASE = "services/metrics_service/"

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
    "labels.py",
    "metric.py",
    "registry.py",
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
            "metrics_service implementation contains forbidden import: "
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
    "services/metrics_service/"
    "_test_metrics.sllmmet"
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


def test_labels():
    labels = LabelSet(
        [
            "service",
            "outcome",
        ],
        {
            "service": "rag",
            "outcome": "ok",
        },
    )

    eq(
        labels.key(),
        "service=rag|outcome=ok",
        "label key uses definition order",
    )

    eq(
        labels.to_dict(),
        {
            "service": "rag",
            "outcome": "ok",
        },
        "label dictionary preserved",
    )


def test_counter():
    manager = MetricsManager()

    manager.define(
        "requests_total",
        "counter",
        label_names=[
            "service",
        ],
    )

    manager.increment(
        "requests_total",
        timestamp=1,
        labels={
            "service": "rag",
        },
    )

    manager.increment(
        "requests_total",
        timestamp=2,
        amount=4,
        labels={
            "service": "rag",
        },
    )

    metric = manager.get_metric(
        "requests_total"
    )

    eq(
        metric[
            "series"
        ][0][
            "value"
        ],
        5.0,
        "counter accumulates increments",
    )

    eq(
        metric[
            "series"
        ][0][
            "samples"
        ],
        2,
        "counter sample count",
    )

    expect_error(
        ValueError,
        lambda: manager.increment(
            "requests_total",
            timestamp=3,
            amount=-1,
            labels={
                "service": "rag",
            },
        ),
        "counter rejects negative increment",
    )


def test_gauge():
    manager = MetricsManager()

    manager.define(
        "active_requests",
        "gauge",
        label_names=[
            "service",
        ],
    )

    manager.set_gauge(
        "active_requests",
        value=10,
        timestamp=1,
        labels={
            "service": "rag",
        },
    )

    manager.increment(
        "active_requests",
        amount=-3,
        timestamp=2,
        labels={
            "service": "rag",
        },
    )

    metric = manager.get_metric(
        "active_requests"
    )

    eq(
        metric[
            "series"
        ][0][
            "value"
        ],
        7.0,
        "gauge supports set and signed increment",
    )


def test_histogram():
    manager = MetricsManager()

    manager.define(
        "latency",
        "histogram",
        buckets=[
            0.1,
            0.5,
            1.0,
        ],
    )

    for index, value in enumerate(
        [
            0.05,
            0.3,
            0.8,
            2.0,
        ]
    ):
        manager.observe(
            "latency",
            value=value,
            timestamp=(
                index
                + 1
            ),
        )

    series = manager.get_metric(
        "latency"
    )[
        "series"
    ][0]

    eq(
        series[
            "count"
        ],
        4,
        "histogram count",
    )

    eq(
        series[
            "sum"
        ],
        3.15,
        "histogram sum",
    )

    eq(
        series[
            "minimum"
        ],
        0.05,
        "histogram minimum",
    )

    eq(
        series[
            "maximum"
        ],
        2.0,
        "histogram maximum",
    )

    eq(
        [
            item[
                "count"
            ]
            for item in series[
                "buckets"
            ]
        ],
        [
            1,
            2,
            3,
        ],
        "histogram cumulative buckets",
    )


def test_series_isolation():
    manager = MetricsManager()

    manager.define(
        "requests",
        "counter",
        label_names=[
            "service",
            "outcome",
        ],
    )

    manager.increment(
        "requests",
        1,
        labels={
            "service": "rag",
            "outcome": "success",
        },
    )

    manager.increment(
        "requests",
        1,
        amount=2,
        labels={
            "service": "rag",
            "outcome": "failure",
        },
    )

    snapshot = manager.get_metric(
        "requests"
    )

    eq(
        snapshot[
            "series_count"
        ],
        2,
        "different label sets produce separate series",
    )

    values = {
        item[
            "labels"
        ][
            "outcome"
        ]: item[
            "value"
        ]
        for item in snapshot[
            "series"
        ]
    }

    eq(
        values,
        {
            "failure": 2.0,
            "success": 1.0,
        },
        "labelled counter values isolated",
    )


def test_label_validation():
    manager = MetricsManager()

    manager.define(
        "x",
        "counter",
        label_names=[
            "service",
        ],
    )

    expect_error(
        ValueError,
        lambda: manager.increment(
            "x",
            1,
            labels={},
        ),
        "missing label rejected",
    )

    expect_error(
        ValueError,
        lambda: manager.increment(
            "x",
            1,
            labels={
                "service": "a",
                "extra": "b",
            },
        ),
        "unknown label rejected",
    )


def test_timestamp_monotonicity():
    manager = MetricsManager()

    manager.define(
        "x",
        "counter",
    )

    manager.increment(
        "x",
        timestamp=10,
    )

    expect_error(
        ValueError,
        lambda: manager.increment(
            "x",
            timestamp=9,
        ),
        "series timestamps cannot move backwards",
    )


def test_snapshot_status():
    manager = (
        build_default_metrics_manager()
    )

    manager.increment(
        "requests_total",
        timestamp=1,
        labels={
            "service": "rag_service",
            "operation": "answer",
            "outcome": "success",
        },
    )

    manager.set_gauge(
        "active_requests",
        value=2,
        timestamp=1,
        labels={
            "service": "rag_service",
        },
    )

    manager.observe(
        "request_duration_seconds",
        value=0.2,
        timestamp=1,
        labels={
            "service": "rag_service",
            "operation": "answer",
        },
    )

    snapshot = manager.snapshot()

    eq(
        snapshot[
            "metric_count"
        ],
        3,
        "default metrics count",
    )

    eq(
        snapshot[
            "series_count"
        ],
        3,
        "default metric series count",
    )

    status = manager.status()

    eq(
        status[
            "total_updates"
        ],
        3,
        "status update count",
    )


def test_persistence_round_trip():
    if os.path.exists(
        STATE_PATH
    ):
        os.remove(
            STATE_PATH
        )

    source = (
        build_default_metrics_manager()
    )

    source.increment(
        "requests_total",
        timestamp=1,
        amount=3,
        labels={
            "service": "rag_service",
            "operation": "answer",
            "outcome": "success",
        },
    )

    source.observe(
        "request_duration_seconds",
        value=0.4,
        timestamp=2,
        labels={
            "service": "rag_service",
            "operation": "answer",
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
        "metrics snapshot written",
    )

    restored = MetricsManager()

    restored.load_state_file(
        STATE_PATH
    )

    eq(
        restored.export_state(),
        before,
        "metrics exact state round trip",
    )


def test_persistence_corruption():
    manager = MetricsManager()

    manager.define(
        "x",
        "counter",
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
        lambda: MetricsManager().load_state_file(
            STATE_PATH
        ),
        "metrics snapshot checksum detects corruption",
    )


def test_service_flow():
    service = MetricsService()

    defined = service.handle(
        ServiceRequest(
            "m1",
            "metrics_service",
            "define",
            payload={
                "name": "requests",
                "metric_type": "counter",
                "label_names": [
                    "service",
                ],
            },
        )
    )

    eq(
        defined.success,
        True,
        "service defines metric",
    )

    updated = service.handle(
        ServiceRequest(
            "m2",
            "metrics_service",
            "increment",
            payload={
                "name": "requests",
                "timestamp": 100,
                "amount": 2,
                "labels": {
                    "service": "rag",
                },
            },
        )
    )

    eq(
        updated.data[
            "metric"
        ][
            "series"
        ][
            "value"
        ],
        2.0,
        "service increments counter",
    )

    snapshot = service.handle(
        ServiceRequest(
            "m3",
            "metrics_service",
            "snapshot",
        )
    )

    eq(
        snapshot.data[
            "snapshot"
        ][
            "series_count"
        ],
        1,
        "service snapshot returns series",
    )


def test_protocol_round_trip():
    manager = MetricsManager()

    manager.define(
        "active",
        "gauge",
        label_names=[
            "service",
        ],
    )

    service = MetricsService(
        manager
    )

    codec = ProtocolCodec()

    request = ServiceRequest(
        "protocol-metrics",
        "metrics_service",
        "set_gauge",
        payload={
            "name": "active",
            "value": 4,
            "timestamp": 10,
            "labels": {
                "service": "rag",
            },
        },
        trace_id="trace-metrics",
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
        "metrics operation survives protocol codec",
    )

    eq(
        response.trace_id,
        "trace-metrics",
        "metrics trace preserved",
    )

    eq(
        response.data[
            "metric"
        ][
            "series"
        ][
            "value"
        ],
        4.0,
        "metric value survives protocol",
    )


def test_errors():
    service = MetricsService()

    missing = service.handle(
        ServiceRequest(
            "e1",
            "metrics_service",
            "increment",
            payload={
                "name": "missing",
                "timestamp": 1,
            },
        )
    )

    eq(
        missing.error.code,
        "NOT_FOUND",
        "undefined metric maps to NOT_FOUND",
    )

    invalid = service.handle(
        ServiceRequest(
            "e2",
            "metrics_service",
            "define",
            payload={
                "name": "x",
                "metric_type": "unknown",
            },
        )
    )

    eq(
        invalid.error.code,
        "INVALID_REQUEST",
        "invalid metric type rejected",
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


def test_definition_validation():
    expect_error(
        ValueError,
        lambda: MetricDefinition(
            "h",
            "histogram",
            buckets=[
                1.0,
                0.5,
            ],
        ),
        "unsorted histogram buckets rejected",
    )

    registry = MetricsRegistry()

    registry.define(
        "x",
        "counter",
    )

    expect_error(
        ValueError,
        lambda: registry.define(
            "x",
            "counter",
        ),
        "duplicate metric definition rejected",
    )


def main():
    try:
        test_labels()
        test_counter()
        test_gauge()
        test_histogram()
        test_series_isolation()
        test_label_validation()
        test_timestamp_monotonicity()
        test_snapshot_status()
        test_persistence_round_trip()
        test_persistence_corruption()
        test_service_flow()
        test_protocol_round_trip()
        test_errors()
        test_definition_validation()

    finally:
        if os.path.exists(
            STATE_PATH
        ):
            os.remove(
                STATE_PATH
            )

    print(
        "METRICS SERVICE TEST SUITE: PASS"
    )
    print(
        "Assertions passed:",
        ASSERTIONS,
    )
    print(
        "Files validated: 6/6"
    )
    print(
        "Counter/gauge/histogram metrics: VALIDATED"
    )
    print(
        "Deterministic labelled series identity: VALIDATED"
    )
    print(
        "Histogram cumulative buckets: VALIDATED"
    )
    print(
        "Per-series timestamp monotonicity: VALIDATED"
    )
    print(
        "Runtime snapshots/status aggregation: VALIDATED"
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
