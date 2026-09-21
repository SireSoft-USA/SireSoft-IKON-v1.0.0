import os
import shutil

PROTOCOL_BASE = "libs/protocol/"
LOGGING_BASE = "services/logging_service/"
METRICS_BASE = "services/metrics_service/"
TRACING_BASE = "services/tracing_service/"
CONCURRENCY_BASE = "runtime/concurrency/"
PROCESSES_BASE = "runtime/processes/"
STORAGE_BASE = "runtime/storage/"
LIFECYCLE_BASE = "runtime/lifecycle/"
BOOTSTRAP_BASE = "runtime/bootstrap/"
HEALTH_BASE = "runtime/health/"
OBSERVABILITY_BASE = "runtime/observability/"
DIAGNOSTICS_BASE = "runtime/diagnostics/"

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
        CONCURRENCY_BASE,
        [
            "future.py",
            "task_queue.py",
            "semaphore.py",
            "worker_pool.py",
            "service_executor.py",
            "network_runner.py",
        ],
    ),
    (
        PROCESSES_BASE,
        [
            "spec.py",
            "process.py",
            "registry.py",
            "supervisor.py",
            "group.py",
        ],
    ),
    (
        STORAGE_BASE,
        [
            "path_policy.py",
            "atomic_file.py",
            "namespace.py",
            "store.py",
        ],
    ),
    (
        LIFECYCLE_BASE,
        [
            "resource.py",
            "graph.py",
            "manager.py",
            "adapters.py",
        ],
    ),
    (
        BOOTSTRAP_BASE,
        [
            "config.py",
            "context.py",
            "application.py",
            "builder.py",
        ],
    ),
    (
        HEALTH_BASE,
        [
            "probe.py",
            "adapters.py",
            "manager.py",
        ],
    ),
    (
        OBSERVABILITY_BASE,
        [
            "context.py",
            "manager.py",
            "dispatcher.py",
            "snapshot.py",
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
    "redactor.py",
    "finding.py",
    "analyzer.py",
    "report.py",
    "collector.py",
]:
    path = (
        DIAGNOSTICS_BASE
        + filename
    )

    source = open(
        path,
        "r",
        encoding="utf-8",
    ).read()

    if "import " in source:
        raise AssertionError(
            "diagnostics implementation contains forbidden import: "
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

ROOT = (
    "runtime/diagnostics/"
    "_test_runtime"
)


def check(
    condition,
    message,
):
    global ASSERTIONS
    ASSERTIONS += 1

    if not condition:
        raise AssertionError(message)


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


def cleanup():
    if os.path.exists(ROOT):
        shutil.rmtree(ROOT)


def build_observability(
    health,
):
    logs = LoggingManager(
        minimum_level="DEBUG",
        max_records=100,
    )

    metrics = MetricsManager()

    tracing = TracingManager(
        metrics_manager=metrics,
    )

    observer = RuntimeObservability(
        logging_manager=logs,
        metrics_manager=metrics,
        tracing_manager=tracing,
        health_manager=health,
    )

    return (
        observer,
        ObservabilitySnapshot(observer),
    )


def test_redactor():
    redactor = DiagnosticRedactor()

    value = redactor.redact({
        "token": "abc",
        "nested": {
            "password": "xyz",
            "safe": "ok",
        },
    })

    eq(
        value["token"],
        "[REDACTED]",
        "top-level secret redacted",
    )

    eq(
        value["nested"]["password"],
        "[REDACTED]",
        "nested secret redacted",
    )

    eq(
        value["nested"]["safe"],
        "ok",
        "safe value preserved",
    )


def test_finding_report():
    finding = DiagnosticFinding(
        "X",
        "warning",
        "something",
        "component",
    )

    report = RuntimeDiagnosticReport(
        report_id="diagnostic-1",
        captured_at=10,
        snapshot={
            "secret": "hidden",
        },
        findings=[
            finding,
        ],
    )

    eq(
        report.status(),
        "warning",
        "warning finding determines report status",
    )

    eq(
        report.to_dict()[
            "snapshot"
        ][
            "secret"
        ],
        "[REDACTED]",
        "report snapshot redacted",
    )


def test_analyzer_rules():
    analyzer = RuntimeDiagnosticAnalyzer()

    findings = analyzer.analyze({
        "runtime": {
            "stopped": False,
            "lifecycle": {
                "phase": "failed",
                "failed_resources": 2,
                "last_error": "boom",
            },
            "worker_pool": {
                "started": True,
                "shutdown": False,
                "alive_workers": 0,
                "total_failed": 3,
            },
        },
        "health": {
            "status": "unhealthy",
            "ready": False,
            "live": False,
            "probes": [
                {
                    "name": "workers",
                    "status": "unhealthy",
                    "error": "dead",
                },
            ],
        },
        "observability": {
            "status": {
                "total_finished": 4,
                "total_error": 1,
                "total_exception": 1,
                "active_by_service": {
                    "svc": 0,
                },
            },
        },
    })

    codes = [
        finding.code
        for finding in findings
    ]

    for expected in (
        "LIFECYCLE_FAILED",
        "WORKERS_UNAVAILABLE",
        "RUNTIME_UNHEALTHY",
        "PROBE_UNHEALTHY",
        "REQUEST_FAILURES_RECORDED",
    ):
        check(
            expected in codes,
            "expected diagnostic finding: "
            + expected,
        )


def test_healthy_integrated_report():
    cleanup()

    app = RuntimeBuilder().build(
        RuntimeBootstrapConfig(
            storage_root=ROOT,
            worker_count=1,
            queue_capacity=4,
        )
    )

    app.start()

    health = RuntimeHealthManager()

    health.register(
        RuntimeHealthAdapters.lifecycle(
            app.context.get(
                "lifecycle"
            )
        )
    )

    health.register(
        RuntimeHealthAdapters.worker_pool(
            app.context.get(
                "worker_pool"
            )
        )
    )

    health.register(
        RuntimeHealthAdapters.storage(
            app.storage()
        )
    )

    observer, snapshot = build_observability(
        health
    )

    request = ServiceRequest(
        "req-ok",
        "diagnostic_service",
        "test",
        trace_id="trace-ok",
    )

    context = observer.begin_request(
        request,
        100,
    )

    observer.finish_response(
        context,
        ServiceResponse.success_response(
            request,
            data={
                "ok": True,
            },
        ),
        101,
    )

    collector = RuntimeDiagnosticCollector(
        runtime_application=app,
        health_manager=health,
        observability_snapshot=snapshot,
    )

    report = collector.collect(
        captured_at=102,
        extra={
            "api_key": "must-hide",
            "environment": "test",
        },
    )

    public = report.to_dict()

    eq(
        public["status"],
        "ok",
        "healthy runtime produces no warning/critical findings",
    )

    eq(
        public["severity_counts"],
        {
            "info": 0,
            "warning": 0,
            "critical": 0,
        },
        "healthy report severity counts",
    )

    eq(
        public["snapshot"][
            "extra"
        ][
            "api_key"
        ],
        "[REDACTED]",
        "collector extra secrets redacted",
    )

    eq(
        public["snapshot"][
            "health"
        ][
            "status"
        ],
        "healthy",
        "collector includes runtime health",
    )

    eq(
        collector.status()[
            "total_reports"
        ],
        1,
        "collector report count",
    )

    app.stop()


def test_stopped_runtime_report():
    cleanup()

    app = RuntimeBuilder().build(
        RuntimeBootstrapConfig(
            storage_root=ROOT,
            worker_count=1,
            queue_capacity=2,
        )
    )

    app.start()
    app.stop()

    collector = RuntimeDiagnosticCollector(
        runtime_application=app,
    )

    report = collector.collect(
        captured_at=200,
    )

    codes = [
        row["code"]
        for row
        in report.to_dict()[
            "findings"
        ]
    ]

    check(
        "RUNTIME_STOPPED"
        in codes,
        "stopped runtime finding emitted",
    )

    eq(
        report.status(),
        "warning",
        "stopped runtime report warning status",
    )


def test_observability_failure_report():
    health = RuntimeHealthManager()

    health.register(
        RuntimeProbe(
            "simple",
            lambda: {
                "status": "healthy",
                "ready": True,
            },
        )
    )

    observer, snapshot = build_observability(
        health
    )

    request = ServiceRequest(
        "req-error",
        "service",
        "op",
    )

    context = observer.begin_request(
        request,
        300,
    )

    observer.finish_response(
        context,
        ServiceResponse.error_response(
            request,
            ProtocolError(
                code="FAILED",
                message="failed",
            ),
        ),
        301,
    )

    collector = RuntimeDiagnosticCollector(
        health_manager=health,
        observability_snapshot=snapshot,
    )

    report = collector.collect(
        captured_at=302,
    )

    codes = [
        row["code"]
        for row
        in report.to_dict()[
            "findings"
        ]
    ]

    check(
        "REQUEST_FAILURES_RECORDED"
        in codes,
        "request failure finding emitted",
    )


def test_missing_runtime_source():
    analyzer = RuntimeDiagnosticAnalyzer()

    findings = analyzer.analyze({
        "runtime": None,
        "health": None,
        "observability": None,
    })

    eq(
        findings[0].code,
        "RUNTIME_STATUS_MISSING",
        "missing runtime status reported",
    )

    eq(
        findings[0].severity,
        "warning",
        "missing runtime status severity",
    )


def test_sequence():
    collector = RuntimeDiagnosticCollector()

    first = collector.collect(
        1
    )

    second = collector.collect(
        2
    )

    eq(
        first.report_id,
        "diagnostic-1",
        "first diagnostic id",
    )

    eq(
        second.report_id,
        "diagnostic-2",
        "second diagnostic id",
    )


def main():
    try:
        test_redactor()
        test_finding_report()
        test_analyzer_rules()
        test_healthy_integrated_report()
        test_stopped_runtime_report()
        test_observability_failure_report()
        test_missing_runtime_source()
        test_sequence()

    finally:
        cleanup()

    print(
        "RUNTIME DIAGNOSTICS TEST SUITE: PASS"
    )
    print(
        "Assertions passed:",
        ASSERTIONS,
    )
    print(
        "Files validated: 5/5"
    )
    print(
        "Structured diagnostic redaction: VALIDATED"
    )
    print(
        "Deterministic runtime findings: VALIDATED"
    )
    print(
        "Bootstrap/runtime status collection: VALIDATED"
    )
    print(
        "Runtime health collection: VALIDATED"
    )
    print(
        "Observability snapshot collection: VALIDATED"
    )
    print(
        "Integrated diagnostic report generation: VALIDATED"
    )
    print(
        "Third-party dependencies: 0"
    )


main()
