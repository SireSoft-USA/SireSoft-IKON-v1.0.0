import os

SERIAL_BASE = "libs/core/serialization/"
PROTOCOL_BASE = "libs/protocol/"
EVENT_BASE = "services/event_bus/"
METRICS_BASE = "services/metrics_service/"
SERVICE_BASE = "services/tracing_service/"

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
        METRICS_BASE,
        [
            "labels.py",
            "metric.py",
            "registry.py",
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
    "span.py",
    "trace.py",
    "sampler.py",
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
            "tracing_service implementation contains forbidden import: "
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
    "services/tracing_service/"
    "_test_tracing.sllmtrc"
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


def test_root_and_child_spans():
    manager = TracingManager()

    root_result = manager.start_span(
        trace_id="trace-1",
        name="request",
        service_name="api_gateway",
        start_time=10,
        operation="POST /v1/chat",
        correlation_id="corr-1",
    )

    root_id = root_result[
        "span"
    ][
        "span_id"
    ]

    child_result = manager.start_span(
        trace_id="trace-1",
        name="rag",
        service_name="rag_service",
        start_time=11,
        parent_span_id=root_id,
        operation="answer",
    )

    child = child_result[
        "span"
    ]

    eq(
        child[
            "parent_span_id"
        ],
        root_id,
        "child span links to root span",
    )

    trace = manager.get_trace(
        "trace-1"
    )

    eq(
        len(
            trace.roots()
        ),
        1,
        "trace has exactly one root",
    )

    eq(
        trace.running_count(),
        2,
        "both spans initially running",
    )


def test_finish_duration_error():
    manager = TracingManager()

    started = manager.start_span(
        "trace-1",
        "inference",
        "inference_service",
        100,
        operation="generate",
    )

    span_id = started[
        "span"
    ][
        "span_id"
    ]

    finished = manager.finish_span(
        "trace-1",
        span_id,
        end_time=107,
        status="error",
        error_type="RuntimeError",
        error_message="generation failed",
    )

    span = finished[
        "span"
    ]

    eq(
        span[
            "duration"
        ],
        7,
        "span duration computed",
    )

    eq(
        span[
            "status"
        ],
        "error",
        "span error status recorded",
    )

    eq(
        manager.status()[
            "total_errors"
        ],
        1,
        "tracing error count",
    )


def test_events_attributes():
    manager = TracingManager()

    started = manager.start_span(
        "trace-1",
        "retrieve",
        "retrieval_service",
        1,
    )

    span_id = started[
        "span"
    ][
        "span_id"
    ]

    manager.set_attribute(
        "trace-1",
        span_id,
        "top_k",
        5,
    )

    span = manager.add_event(
        "trace-1",
        span_id,
        "index_searched",
        2,
        attributes={
            "documents": 10,
        },
    )

    eq(
        span[
            "attributes"
        ][
            "top_k"
        ],
        5,
        "span attribute stored",
    )

    eq(
        span[
            "events"
        ][0][
            "name"
        ],
        "index_searched",
        "span event stored",
    )


def test_parent_validation():
    manager = TracingManager()

    expect_error(
        KeyError,
        lambda: manager.start_span(
            "trace-1",
            "child",
            "rag_service",
            1,
            parent_span_id="missing",
        ),
        "missing parent span rejected",
    )


def test_sampler():
    none = TracingManager(
        sampler=(
            DeterministicTraceSampler(
                0,
                1,
            )
        )
    )

    dropped = none.start_span(
        "trace-drop",
        "request",
        "gateway",
        1,
    )

    eq(
        dropped[
            "sampled"
        ],
        False,
        "zero-rate sampler drops trace",
    )

    eq(
        none.status()[
            "total_dropped"
        ],
        1,
        "dropped trace counted",
    )

    half = (
        DeterministicTraceSampler(
            1,
            2,
        )
    )

    eq(
        half.should_sample(
            "stable-trace"
        ),
        half.should_sample(
            "stable-trace"
        ),
        "hash sampler deterministic for same trace ID",
    )


def test_metrics_integration():
    metrics = MetricsManager()

    manager = TracingManager(
        metrics_manager=metrics
    )

    started = manager.start_span(
        "trace-1",
        "answer",
        "rag_service",
        10,
        operation="answer",
    )

    manager.finish_span(
        "trace-1",
        started[
            "span"
        ][
            "span_id"
        ],
        14,
        status="ok",
    )

    started_metric = metrics.get_metric(
        "trace_spans_started_total"
    )

    eq(
        started_metric[
            "series"
        ][0][
            "value"
        ],
        1.0,
        "span start updates metrics counter",
    )

    finished_metric = metrics.get_metric(
        "trace_spans_finished_total"
    )

    eq(
        finished_metric[
            "series"
        ][0][
            "labels"
        ][
            "status"
        ],
        "ok",
        "finished metric labelled by status",
    )

    duration_metric = metrics.get_metric(
        "trace_span_duration_seconds"
    )

    eq(
        duration_metric[
            "series"
        ][0][
            "count"
        ],
        1,
        "span duration histogram observed",
    )

    eq(
        duration_metric[
            "series"
        ][0][
            "sum"
        ],
        4.0,
        "span duration value observed",
    )


def test_event_bus_integration():
    bus = EventBusManager()
    seen = []

    bus.subscribe(
        "trace-events",
        "tracing.",
        lambda event: seen.append(
            event.topic
        ),
        mode="prefix",
    )

    manager = TracingManager(
        event_bus=bus
    )

    started = manager.start_span(
        "trace-1",
        "request",
        "api_gateway",
        1,
        correlation_id="corr-1",
    )

    manager.finish_span(
        "trace-1",
        started[
            "span"
        ][
            "span_id"
        ],
        2,
    )

    eq(
        seen,
        [
            "tracing.span_started",
            "tracing.span_finished",
        ],
        "trace lifecycle events published",
    )

    history = bus.history(
        topic="tracing.span_finished"
    )

    eq(
        history[
            "events"
        ][0][
            "correlation_id"
        ],
        "corr-1",
        "trace correlation propagated to event bus",
    )


def test_list_filter():
    manager = TracingManager(
        sampler=(
            DeterministicTraceSampler(
                1,
                1,
            )
        )
    )

    manager.start_span(
        "a",
        "x",
        "svc",
        1,
    )

    manager.start_span(
        "b",
        "x",
        "svc",
        1,
    )

    traces = manager.list_traces(
        sampled=True,
        limit=1,
        newest_first=True,
    )

    eq(
        len(
            traces
        ),
        1,
        "trace listing respects limit",
    )

    eq(
        traces[
            0
        ][
            "trace_id"
        ],
        "b",
        "newest-first trace listing",
    )


def test_persistence_round_trip():
    if os.path.exists(
        STATE_PATH
    ):
        os.remove(
            STATE_PATH
        )

    source = TracingManager()

    root = source.start_span(
        "trace-1",
        "request",
        "api_gateway",
        10,
        operation="chat",
        attributes={
            "route": "/v1/chat",
        },
    )

    child = source.start_span(
        "trace-1",
        "rag",
        "rag_service",
        11,
        parent_span_id=root[
            "span"
        ][
            "span_id"
        ],
    )

    source.add_event(
        "trace-1",
        child[
            "span"
        ][
            "span_id"
        ],
        "retrieved",
        12,
        attributes={
            "chunks": 4,
        },
    )

    source.finish_span(
        "trace-1",
        child[
            "span"
        ][
            "span_id"
        ],
        13,
    )

    before = source.export_state()

    saved = source.save_state(
        STATE_PATH
    )

    check(
        saved[
            "bytes"
        ] > 0,
        "tracing snapshot written",
    )

    restored = TracingManager()

    restored.load_state_file(
        STATE_PATH
    )

    eq(
        restored.export_state(),
        before,
        "tracing exact state round trip",
    )


def test_persistence_corruption():
    manager = TracingManager()

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
        lambda: TracingManager().load_state_file(
            STATE_PATH
        ),
        "tracing checksum detects corruption",
    )


def test_service_flow():
    service = TracingService()

    started = service.handle(
        ServiceRequest(
            "s1",
            "tracing_service",
            "start_span",
            payload={
                "trace_id": "trace-svc",
                "name": "request",
                "service_name": "api_gateway",
                "start_time": 100,
                "operation": "chat",
            },
            correlation_id="corr-svc",
        )
    )

    eq(
        started.success,
        True,
        "service starts span",
    )

    span_id = started.data[
        "trace"
    ][
        "span"
    ][
        "span_id"
    ]

    finished = service.handle(
        ServiceRequest(
            "s2",
            "tracing_service",
            "finish_span",
            payload={
                "trace_id": "trace-svc",
                "span_id": span_id,
                "end_time": 103,
                "status": "ok",
            },
        )
    )

    eq(
        finished.data[
            "trace"
        ][
            "span"
        ][
            "duration"
        ],
        3,
        "service finishes span",
    )


def test_protocol_round_trip():
    service = TracingService()
    codec = ProtocolCodec()

    request = ServiceRequest(
        "protocol-trace",
        "tracing_service",
        "start_span",
        payload={
            "trace_id": "trace-protocol",
            "name": "retrieve",
            "service_name": "retrieval_service",
            "start_time": 5,
            "attributes": {
                "top_k": 5,
            },
        },
        trace_id="request-trace",
        correlation_id="request-correlation",
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
        "tracing operation survives protocol codec",
    )

    eq(
        response.trace_id,
        "request-trace",
        "service request trace preserved by protocol",
    )

    eq(
        response.data[
            "trace"
        ][
            "span"
        ][
            "attributes"
        ][
            "top_k"
        ],
        5,
        "span attributes survive protocol",
    )


def test_errors():
    service = TracingService()

    missing = service.handle(
        ServiceRequest(
            "e1",
            "tracing_service",
            "get_trace",
            payload={
                "trace_id": "missing",
            },
        )
    )

    eq(
        missing.error.code,
        "NOT_FOUND",
        "missing trace maps to NOT_FOUND",
    )

    invalid = service.handle(
        ServiceRequest(
            "e2",
            "tracing_service",
            "start_span",
            payload={
                "trace_id": "",
                "name": "x",
                "service_name": "svc",
                "start_time": 1,
            },
        )
    )

    eq(
        invalid.error.code,
        "INVALID_REQUEST",
        "invalid trace maps to INVALID_REQUEST",
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
        "wrong target service rejected",
    )

    expect_error(
        TypeError,
        lambda: service.handle(
            {}
        ),
        "non-ServiceRequest rejected",
    )


def test_double_finish():
    manager = TracingManager()

    started = manager.start_span(
        "trace-1",
        "x",
        "svc",
        1,
    )

    span_id = started[
        "span"
    ][
        "span_id"
    ]

    manager.finish_span(
        "trace-1",
        span_id,
        2,
    )

    expect_error(
        RuntimeError,
        lambda: manager.finish_span(
            "trace-1",
            span_id,
            3,
        ),
        "double finish rejected",
    )


def main():
    try:
        test_root_and_child_spans()
        test_finish_duration_error()
        test_events_attributes()
        test_parent_validation()
        test_sampler()
        test_metrics_integration()
        test_event_bus_integration()
        test_list_filter()
        test_persistence_round_trip()
        test_persistence_corruption()
        test_service_flow()
        test_protocol_round_trip()
        test_errors()
        test_double_finish()

    finally:
        if os.path.exists(
            STATE_PATH
        ):
            os.remove(
                STATE_PATH
            )

    print(
        "TRACING SERVICE TEST SUITE: PASS"
    )
    print(
        "Assertions passed:",
        ASSERTIONS,
    )
    print(
        "Files validated: 6/6"
    )
    print(
        "Root/child span relationships: VALIDATED"
    )
    print(
        "Span lifecycle/duration/errors: VALIDATED"
    )
    print(
        "Deterministic trace sampling: VALIDATED"
    )
    print(
        "Span attributes/events: VALIDATED"
    )
    print(
        "Metrics service integration: VALIDATED"
    )
    print(
        "Event-bus lifecycle publication: VALIDATED"
    )
    print(
        "Checksum-protected tracing persistence: VALIDATED"
    )
    print(
        "Protocol service operations: VALIDATED"
    )
    print(
        "Third-party dependencies: 0"
    )


main()
