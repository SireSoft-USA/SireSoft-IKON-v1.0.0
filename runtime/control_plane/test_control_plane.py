import os
import shutil

PROTOCOL_BASE = "libs/protocol/"
CONCURRENCY_BASE = "runtime/concurrency/"
PROCESSES_BASE = "runtime/processes/"
STORAGE_BASE = "runtime/storage/"
LIFECYCLE_BASE = "runtime/lifecycle/"
BOOTSTRAP_BASE = "runtime/bootstrap/"
SIGNALS_BASE = "runtime/signals/"
DIAGNOSTICS_BASE = "runtime/diagnostics/"
RECOVERY_BASE = "runtime/recovery/"
LOAD_BALANCER_BASE = "services/load_balancer/"
DISCOVERY_BASE = "services/service_discovery/"
HOST_BASE = "runtime/service_host/"
MAINTENANCE_BASE = "runtime/maintenance/"
CONTROL_BASE = "runtime/control_plane/"

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
        SIGNALS_BASE,
        [
            "event.py",
            "coordinator.py",
            "runtime_bridge.py",
        ],
    ),
    (
        DIAGNOSTICS_BASE,
        [
            "redactor.py",
            "finding.py",
            "analyzer.py",
            "report.py",
            "collector.py",
        ],
    ),
    (
        RECOVERY_BASE,
        [
            "action.py",
            "plan.py",
            "policy.py",
            "executor.py",
            "adapters.py",
            "manager.py",
        ],
    ),
    (
        LOAD_BALANCER_BASE,
        [
            "instance.py",
            "registry.py",
            "strategies.py",
            "load_balancer.py",
        ],
    ),
    (
        DISCOVERY_BASE,
        [
            "descriptor.py",
            "registry.py",
            "manager.py",
        ],
    ),
    (
        HOST_BASE,
        [
            "binding.py",
            "registry.py",
            "host.py",
            "gateway_dispatcher.py",
        ],
    ),
    (
        MAINTENANCE_BASE,
        [
            "state.py",
            "snapshot.py",
            "drain.py",
            "manager.py",
            "dispatcher.py",
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
    "result.py",
    "controller.py",
    "service.py",
]:
    path = CONTROL_BASE + filename

    source = open(
        path,
        "r",
        encoding="utf-8",
    ).read()

    if "import " in source:
        raise AssertionError(
            "control-plane implementation contains forbidden import: "
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
    "runtime/control_plane/"
    "_test_runtime"
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


def cleanup():
    if os.path.exists(
        ROOT
    ):
        shutil.rmtree(
            ROOT
        )


def build():
    cleanup()

    app = RuntimeBuilder().build(
        RuntimeBootstrapConfig(
            storage_root=ROOT,
            worker_count=1,
            queue_capacity=4,
        )
    )

    app.start()

    host = ServiceHost()

    host.add_service(
        "echo-1",
        "echo_service",
        lambda request: (
            ServiceResponse
            .success_response(
                request,
                data={
                    "ok": True,
                },
            )
        ),
    )

    host.start(
        1
    )

    maintenance = (
        RuntimeMaintenanceManager(
            host
        )
    )

    diagnostics = (
        RuntimeDiagnosticCollector(
            runtime_application=app,
        )
    )

    recovery = RecoveryManager()

    shutdown = (
        ShutdownCoordinator()
    )

    controller = RuntimeControlPlane(
        runtime_application=app,
        diagnostic_collector=diagnostics,
        recovery_manager=recovery,
        maintenance_manager=maintenance,
        shutdown_coordinator=shutdown,
    )

    service = RuntimeControlService(
        controller
    )

    return (
        app,
        host,
        controller,
        service,
        shutdown,
    )


def request(
    operation,
    payload=None,
):
    return ServiceRequest(
        request_id=(
            "req-"
            + operation
        ),
        service=(
            "runtime_control"
        ),
        operation=operation,
        payload=(
            {}
            if payload is None
            else payload
        ),
    )


def test_status():
    (
        app,
        host,
        controller,
        service,
        shutdown,
    ) = build()

    response = service.handle(
        request(
            "status"
        )
    )

    eq(
        response.success,
        True,
        "control status succeeds",
    )

    eq(
        response.data[
            "operation"
        ],
        "status",
        "control status operation label",
    )

    eq(
        response.data[
            "data"
        ][
            "runtime"
        ][
            "running"
        ],
        True,
        "control status includes runtime state",
    )

    host.stop()
    app.stop()


def test_diagnostics_and_report_registry():
    (
        app,
        host,
        controller,
        service,
        shutdown,
    ) = build()

    response = service.handle(
        request(
            "diagnostics",
            {
                "captured_at": 10,
                "extra": {
                    "secret": (
                        "do-not-expose"
                    ),
                },
            },
        )
    )

    eq(
        response.success,
        True,
        "diagnostics operation succeeds",
    )

    report = response.data[
        "data"
    ][
        "report"
    ]

    eq(
        report[
            "snapshot"
        ][
            "extra"
        ][
            "secret"
        ],
        "[REDACTED]",
        "diagnostic report is redacted",
    )

    listed = service.handle(
        request(
            "list_reports"
        )
    )

    eq(
        len(
            listed.data[
                "data"
            ][
                "report_ids"
            ]
        ),
        1,
        "diagnostic report registered for later recovery planning",
    )

    host.stop()
    app.stop()


def test_recovery_plan_default_safe():
    (
        app,
        host,
        controller,
        service,
        shutdown,
    ) = build()

    diagnostic = service.handle(
        request(
            "diagnostics",
            {
                "captured_at": 20,
            },
        )
    )

    report_id = (
        diagnostic.data[
            "data"
        ][
            "report"
        ][
            "report_id"
        ]
    )

    plan = service.handle(
        request(
            "recovery_plan",
            {
                "report_id": (
                    report_id
                ),
            },
        )
    )

    eq(
        plan.success,
        True,
        "recovery plan succeeds",
    )

    recovered = service.handle(
        request(
            "recover",
            {
                "report_id": (
                    report_id
                ),
            },
        )
    )

    eq(
        recovered.success,
        True,
        "default recovery request succeeds safely",
    )

    eq(
        recovered.data[
            "data"
        ][
            "dry_run"
        ],
        True,
        "recovery defaults to dry-run",
    )

    eq(
        recovered.data[
            "changed"
        ],
        False,
        "dry-run does not mutate runtime",
    )

    host.stop()
    app.stop()


def test_maintenance_operations():
    (
        app,
        host,
        controller,
        service,
        shutdown,
    ) = build()

    begun = service.handle(
        request(
            "begin_maintenance",
            {
                "now": 30,
                "reason": "upgrade",
            },
        )
    )

    eq(
        begun.success,
        True,
        "begin maintenance succeeds",
    )

    eq(
        begun.data[
            "data"
        ][
            "maintenance"
        ][
            "mode"
        ],
        "draining",
        "begin maintenance enters draining",
    )

    advanced = service.handle(
        request(
            "advance_maintenance",
            {
                "now": 31,
            },
        )
    )

    eq(
        advanced.data[
            "data"
        ][
            "maintenance"
        ][
            "mode"
        ],
        "maintenance",
        "idle runtime advances to maintenance",
    )

    exited = service.handle(
        request(
            "exit_maintenance",
            {
                "now": 32,
            },
        )
    )

    eq(
        exited.data[
            "data"
        ][
            "maintenance"
        ][
            "mode"
        ],
        "normal",
        "maintenance exits to normal",
    )

    host.stop()
    app.stop()


def test_shutdown_request():
    (
        app,
        host,
        controller,
        service,
        shutdown,
    ) = build()

    first = service.handle(
        request(
            "request_shutdown",
            {
                "reason": (
                    "operator requested"
                ),
                "metadata": {
                    "source": (
                        "control-plane-test"
                    ),
                },
            },
        )
    )

    eq(
        first.success,
        True,
        "shutdown request succeeds",
    )

    eq(
        first.data[
            "changed"
        ],
        True,
        "first shutdown request changes coordinator state",
    )

    second = service.handle(
        request(
            "request_shutdown",
            {
                "reason": (
                    "second request"
                ),
            },
        )
    )

    eq(
        second.data[
            "changed"
        ],
        False,
        "repeated shutdown request is idempotent",
    )

    eq(
        shutdown.event()
        .reason,
        "operator requested",
        "first shutdown reason remains canonical",
    )

    host.stop()
    app.stop()


def test_wrong_target_and_unknown_operation():
    (
        app,
        host,
        controller,
        service,
        shutdown,
    ) = build()

    wrong = ServiceRequest(
        "wrong",
        "other_service",
        "status",
    )

    response = service.handle(
        wrong
    )

    eq(
        response.success,
        False,
        "wrong service target rejected",
    )

    eq(
        response.error.code,
        "WRONG_SERVICE_TARGET",
        "wrong target error code",
    )

    unknown = service.handle(
        request(
            "does_not_exist"
        )
    )

    eq(
        unknown.error.code,
        "UNKNOWN_OPERATION",
        "unknown operation rejected",
    )

    host.stop()
    app.stop()


def test_validation_failure():
    (
        app,
        host,
        controller,
        service,
        shutdown,
    ) = build()

    response = service.handle(
        request(
            "begin_maintenance",
            {
                "reason": "missing-now",
            },
        )
    )

    eq(
        response.success,
        False,
        "invalid control operation returns protocol error",
    )

    eq(
        response.error.code,
        "CONTROL_OPERATION_FAILED",
        "validation failure error code",
    )

    host.stop()
    app.stop()


def test_controller_counters():
    (
        app,
        host,
        controller,
        service,
        shutdown,
    ) = build()

    controller.status()

    controller.request_shutdown(
        "counter-test"
    )

    result = controller.status()

    eq(
        result.data[
            "control"
        ][
            "total_operations"
        ],
        3,
        "control status reports the current operation count",
    )

    eq(
        controller.total_operations,
        3,
        "controller total operation counter includes all calls",
    )

    eq(
        controller.total_mutations,
        1,
        "controller mutation counter",
    )

    host.stop()
    app.stop()


def main():
    try:
        test_status()
        test_diagnostics_and_report_registry()
        test_recovery_plan_default_safe()
        test_maintenance_operations()
        test_shutdown_request()
        test_wrong_target_and_unknown_operation()
        test_validation_failure()
        test_controller_counters()

    finally:
        cleanup()

    print(
        "RUNTIME CONTROL PLANE TEST SUITE: PASS"
    )
    print(
        "Assertions passed:",
        ASSERTIONS,
    )
    print(
        "Files validated: 3/3"
    )
    print(
        "Runtime status control surface: VALIDATED"
    )
    print(
        "Diagnostic report collection/registry: VALIDATED"
    )
    print(
        "Dry-run-first recovery operations: VALIDATED"
    )
    print(
        "Maintenance orchestration: VALIDATED"
    )
    print(
        "Idempotent shutdown requests: VALIDATED"
    )
    print(
        "Protocol-facing runtime control service: VALIDATED"
    )
    print(
        "Third-party dependencies: 0"
    )


main()
