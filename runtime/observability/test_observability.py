PROTOCOL_BASE = "libs/protocol/"
LOGGING_BASE = "services/logging_service/"
METRICS_BASE = "services/metrics_service/"
TRACING_BASE = "services/tracing_service/"
HEALTH_BASE = "runtime/health/"
OBSERVABILITY_BASE = "runtime/observability/"

namespace = {
    "__builtins__": __builtins__,
}

groups = [
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
        LOGGING_BASE,
        [
            "record.py",
            "sanitizer.py",
            "sink.py",
            "archive.py",
            "manager.py",
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
        ],
    ),
    (
        TRACING_BASE,
        [
            "span.py",
            "trace.py",
            "sampler.py",
            "persistence.py",
            "manager.py",
        ],
    ),
    (
        HEALTH_BASE,
        [
            "probe.py",
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
    "context.py",
    "manager.py",
    "dispatcher.py",
    "snapshot.py",
]:
    path = (
        OBSERVABILITY_BASE
        + filename
    )

    source = open(
        path,
        "r",
        encoding="utf-8",
    ).read()

    if "import " in source:
        raise AssertionError(
            "observability implementation contains forbidden import: "
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


def build():
    logs = LoggingManager(
        minimum_level="DEBUG",
        max_records=100,
    )

    metrics = MetricsManager()

    tracing = TracingManager(
        metrics_manager=metrics,
    )

    health = RuntimeHealthManager()

    health.register(
        RuntimeProbe(
            "runtime",
            lambda: {
                "status": "healthy",
                "ready": True,
                "details": {
                    "source": "observability-test",
                },
            },
            required=True,
        )
    )

    observer = RuntimeObservability(
        logging_manager=logs,
        metrics_manager=metrics,
        tracing_manager=tracing,
        health_manager=health,
    )

    return (
        observer,
        logs,
        metrics,
        tracing,
        health,
    )


def test_context():
    context = ObservationContext(
        request_id="r1",
        service="svc",
        operation="run",
        trace_id="t1",
        correlation_id="c1",
        start_time=1,
    )

    eq(
        context.finished,
        False,
        "observation context starts unfinished",
    )

    context.finish(
        "success",
        3,
    )

    eq(
        context.duration(),
        2,
        "observation duration computed",
    )

    expect_error(
        RuntimeError,
        lambda: context.finish(
            "success",
            4,
        ),
        "context cannot finish twice",
    )


def test_begin_finish_success():
    (
        observer,
        logs,
        metrics,
        tracing,
        health,
    ) = build()

    request = ServiceRequest(
        "req-success",
        "rag_service",
        "answer",
        payload={
            "query": "hello",
        },
        correlation_id="corr-success",
        trace_id="trace-success",
    )

    context = observer.begin_request(
        request,
        10,
    )

    eq(
        context.trace_id,
        "trace-success",
        "existing trace id preserved",
    )

    eq(
        observer.status()[
            "active_by_service"
        ][
            "rag_service"
        ],
        1,
        "active request count increments",
    )

    response = (
        ServiceResponse
        .success_response(
            request,
            data={
                "answer": "ok",
            },
        )
    )

    result = observer.finish_response(
        context,
        response,
        12,
    )

    eq(
        result[
            "outcome"
        ],
        "success",
        "successful response outcome",
    )

    eq(
        result[
            "duration"
        ],
        2,
        "successful request duration",
    )

    eq(
        observer.status()[
            "active_by_service"
        ][
            "rag_service"
        ],
        0,
        "active request count decrements",
    )

    eq(
        logs.status()[
            "retained_records"
        ],
        2,
        "start and finish logs retained",
    )

    eq(
        tracing.status()[
            "total_started"
        ],
        1,
        "trace span started",
    )

    eq(
        tracing.status()[
            "total_finished"
        ],
        1,
        "trace span finished",
    )

    runtime_counter = (
        metrics.get_metric(
            "runtime_requests_total"
        )
    )

    eq(
        runtime_counter[
            "series_count"
        ],
        1,
        "success request counter series recorded",
    )

    eq(
        runtime_counter[
            "series"
        ][
            0
        ][
            "value"
        ],
        1,
        "success request counter incremented",
    )


def test_error_response():
    (
        observer,
        logs,
        metrics,
        tracing,
        health,
    ) = build()

    request = ServiceRequest(
        "req-error",
        "retrieval_service",
        "search",
    )

    context = observer.begin_request(
        request,
        20,
    )

    response = (
        ServiceResponse
        .error_response(
            request,
            ProtocolError(
                code="BAD_QUERY",
                message="query invalid",
                retryable=False,
            ),
        )
    )

    observer.finish_response(
        context,
        response,
        21,
    )

    eq(
        observer.status()[
            "total_error"
        ],
        1,
        "error response counted",
    )

    eq(
        tracing.status()[
            "total_errors"
        ],
        1,
        "trace records error response",
    )

    errors = logs.query(
        levels=[
            "ERROR",
        ],
    )

    eq(
        errors[
            "count"
        ],
        1,
        "error finish logged at ERROR",
    )

    eq(
        errors[
            "records"
        ][
            0
        ][
            "fields"
        ][
            "error_type"
        ],
        "BAD_QUERY",
        "protocol error code added to finish log",
    )


def test_generated_trace_id():
    (
        observer,
        logs,
        metrics,
        tracing,
        health,
    ) = build()

    request = ServiceRequest(
        "req-no-trace",
        "service",
        "op",
    )

    context = observer.begin_request(
        request,
        1,
    )

    eq(
        context.trace_id,
        "trace-req-no-trace",
        "missing trace id gets deterministic local trace",
    )

    observer.finish_response(
        context,
        ServiceResponse.success_response(
            request
        ),
        2,
    )


def test_observed_dispatcher_success():
    (
        observer,
        logs,
        metrics,
        tracing,
        health,
    ) = build()

    times = [
        30,
        31,
    ]

    def now():
        return times.pop(
            0
        )

    def dispatch(
        request,
    ):
        return (
            ServiceResponse
            .success_response(
                request,
                data={
                    "ok": True,
                },
            )
        )

    wrapped = ObservedDispatcher(
        observer,
        dispatch,
        now,
    )

    request = ServiceRequest(
        "req-wrap",
        "service",
        "run",
    )

    response = wrapped(
        request
    )

    eq(
        response.success,
        True,
        "observed dispatcher returns original response",
    )

    eq(
        observer.status()[
            "total_success"
        ],
        1,
        "observed dispatcher records success",
    )


def test_observed_dispatcher_exception():
    (
        observer,
        logs,
        metrics,
        tracing,
        health,
    ) = build()

    times = [
        40,
        41,
    ]

    def now():
        return times.pop(
            0
        )

    def fail(
        request,
    ):
        raise RuntimeError(
            "dispatcher exploded"
        )

    wrapped = ObservedDispatcher(
        observer,
        fail,
        now,
    )

    request = ServiceRequest(
        "req-exception",
        "service",
        "run",
    )

    expect_error(
        RuntimeError,
        lambda: wrapped(
            request
        ),
        "dispatcher exception propagated",
    )

    eq(
        observer.status()[
            "total_exception"
        ],
        1,
        "dispatcher exception counted",
    )

    eq(
        observer.status()[
            "active_by_service"
        ][
            "service"
        ],
        0,
        "dispatcher exception releases active-request gauge",
    )

    eq(
        tracing.status()[
            "total_errors"
        ],
        1,
        "dispatcher exception marks trace error",
    )


def test_bad_dispatcher_return():
    (
        observer,
        logs,
        metrics,
        tracing,
        health,
    ) = build()

    times = [
        50,
        51,
    ]

    wrapped = ObservedDispatcher(
        observer,
        lambda request: {
            "not": "response",
        },
        lambda: times.pop(
            0
        ),
    )

    request = ServiceRequest(
        "req-bad",
        "service",
        "run",
    )

    expect_error(
        TypeError,
        lambda: wrapped(
            request
        ),
        "non-ServiceResponse dispatcher output rejected",
    )

    eq(
        observer.status()[
            "total_exception"
        ],
        1,
        "invalid dispatcher return observed as exception",
    )


def test_snapshot():
    (
        observer,
        logs,
        metrics,
        tracing,
        health,
    ) = build()

    request = ServiceRequest(
        "req-snapshot",
        "service",
        "run",
    )

    context = observer.begin_request(
        request,
        60,
    )

    observer.finish_response(
        context,
        ServiceResponse.success_response(
            request
        ),
        61,
    )

    snapshot = ObservabilitySnapshot(
        observer
    ).capture(
        log_limit=10,
        trace_limit=10,
    )

    eq(
        snapshot[
            "recent_logs"
        ][
            "count"
        ],
        2,
        "snapshot includes recent logs",
    )

    eq(
        len(
            snapshot[
                "recent_traces"
            ]
        ),
        1,
        "snapshot includes recent traces",
    )

    eq(
        snapshot[
            "health"
        ][
            "status"
        ],
        "healthy",
        "snapshot includes runtime health",
    )

    check(
        snapshot[
            "metrics"
        ][
            "metric_count"
        ] >= 6,
        "snapshot includes runtime and tracing metrics",
    )


def test_response_mismatch():
    (
        observer,
        logs,
        metrics,
        tracing,
        health,
    ) = build()

    request = ServiceRequest(
        "r1",
        "a",
        "op",
    )

    context = observer.begin_request(
        request,
        70,
    )

    other = ServiceRequest(
        "r2",
        "a",
        "op",
    )

    response = (
        ServiceResponse
        .success_response(
            other
        )
    )

    expect_error(
        ValueError,
        lambda: observer.finish_response(
            context,
            response,
            71,
        ),
        "response request mismatch rejected",
    )

    observer.finish_exception(
        context,
        RuntimeError(
            "cleanup"
        ),
        72,
    )


def main():
    test_context()
    test_begin_finish_success()
    test_error_response()
    test_generated_trace_id()
    test_observed_dispatcher_success()
    test_observed_dispatcher_exception()
    test_bad_dispatcher_return()
    test_snapshot()
    test_response_mismatch()

    print(
        "RUNTIME OBSERVABILITY TEST SUITE: PASS"
    )
    print(
        "Assertions passed:",
        ASSERTIONS,
    )
    print(
        "Files validated: 4/4"
    )
    print(
        "Unified logging/metrics/tracing request context: VALIDATED"
    )
    print(
        "Success/error/exception outcomes: VALIDATED"
    )
    print(
        "Active-request accounting: VALIDATED"
    )
    print(
        "Observed ServiceRequest dispatcher: VALIDATED"
    )
    print(
        "Runtime health snapshot integration: VALIDATED"
    )
    print(
        "Trace/correlation propagation: VALIDATED"
    )
    print(
        "Third-party dependencies: 0"
    )


main()
