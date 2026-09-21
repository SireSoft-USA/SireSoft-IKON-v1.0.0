PROTOCOL_BASE = "libs/protocol/"
LOAD_BALANCER_BASE = "services/load_balancer/"
DISCOVERY_BASE = "services/service_discovery/"
CONCURRENCY_BASE = "runtime/concurrency/"
HOST_BASE = "runtime/service_host/"
DIAGNOSTICS_BASE = "runtime/diagnostics/"
RECOVERY_BASE = "runtime/recovery/"

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
        HOST_BASE,
        [
            "binding.py",
            "registry.py",
            "host.py",
            "gateway_dispatcher.py",
            "lifecycle_adapter.py",
        ],
    ),
    (
        DIAGNOSTICS_BASE,
        [
            "redactor.py",
            "finding.py",
            "analyzer.py",
            "report.py",
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
    "action.py",
    "plan.py",
    "policy.py",
    "executor.py",
    "adapters.py",
    "manager.py",
]:
    path = RECOVERY_BASE + filename

    source = open(
        path,
        "r",
        encoding="utf-8",
    ).read()

    if "import " in source:
        raise AssertionError(
            "recovery implementation contains forbidden import: "
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


def report_with_findings(
    findings,
):
    return RuntimeDiagnosticReport(
        report_id="diagnostic-test",
        captured_at=1,
        snapshot={},
        findings=findings,
    )


def test_action_state_machine():
    action = RecoveryAction(
        "a1",
        "x",
        "target",
        "CODE",
        automatic=True,
    )

    eq(
        action.status,
        "planned",
        "action starts planned",
    )

    action.mark_running()

    eq(
        action.status,
        "running",
        "action enters running",
    )

    action.mark_succeeded({
        "ok": True,
    })

    eq(
        action.status,
        "succeeded",
        "action success state",
    )

    eq(
        action.result["ok"],
        True,
        "action stores result",
    )


def test_policy_manual_vs_automatic():
    policy = RecoveryPolicy()

    automatic = policy.propose(
        {
            "code": "PROBE_UNHEALTHY",
            "component": "svc-1",
            "severity": "warning",
            "message": "bad",
        },
        "a1",
    )

    manual = policy.propose(
        {
            "code": "LIFECYCLE_FAILED",
            "component": "lifecycle",
            "severity": "critical",
            "message": "bad",
        },
        "a2",
    )

    eq(
        automatic.automatic,
        True,
        "probe unhealthy is automatic by default",
    )

    eq(
        manual.automatic,
        False,
        "lifecycle failure requires manual review",
    )

    eq(
        manual.action_type,
        "manual_review",
        "critical lifecycle issue maps to manual review",
    )


def test_manager_builds_plan():
    report = report_with_findings([
        DiagnosticFinding(
            "PROBE_UNHEALTHY",
            "warning",
            "probe down",
            "svc-1",
        ),
        DiagnosticFinding(
            "LIFECYCLE_FAILED",
            "critical",
            "lifecycle failed",
            "lifecycle",
        ),
    ])

    manager = RecoveryManager()

    plan = manager.plan(report)

    eq(
        len(plan.actions),
        2,
        "recovery plan action count",
    )

    eq(
        len(plan.automatic_actions()),
        1,
        "recovery plan automatic count",
    )

    eq(
        len(plan.manual_actions()),
        1,
        "recovery plan manual count",
    )


def test_dry_run():
    executor = RecoveryExecutor()

    executor.register(
        "mark_component_healthy",
        lambda action: {
            "done": True,
        },
    )

    action = RecoveryAction(
        "a1",
        "mark_component_healthy",
        "svc-1",
        "PROBE_UNHEALTHY",
        automatic=True,
    )

    executor.execute(
        action,
        dry_run=True,
    )

    eq(
        action.status,
        "skipped",
        "dry-run skips real recovery execution",
    )

    eq(
        executor.status()[
            "total_executed"
        ],
        0,
        "dry-run does not execute handler",
    )


def test_manual_action_not_executed():
    executor = RecoveryExecutor()

    action = RecoveryAction(
        "a1",
        "manual_review",
        "runtime",
        "RUNTIME_UNHEALTHY",
        automatic=False,
    )

    executor.execute(action)

    eq(
        action.status,
        "skipped",
        "manual action skipped without approval",
    )


def test_service_host_recovery_adapter():
    host = ServiceHost()

    host.add_service(
        "svc-1",
        "echo_service",
        lambda request: (
            ServiceResponse.success_response(
                request,
                data={
                    "ok": True,
                },
            )
        ),
    )

    host.start(1)

    host.mark_unhealthy(
        "svc-1"
    )

    response = host.dispatch(
        ServiceRequest(
            "r1",
            "echo_service",
            "echo",
        )
    )

    eq(
        response.success,
        False,
        "unhealthy hosted instance does not receive traffic",
    )

    report = report_with_findings([
        DiagnosticFinding(
            "PROBE_UNHEALTHY",
            "warning",
            "hosted instance unhealthy",
            "svc-1",
        ),
    ])

    executor = RecoveryExecutor()

    executor.register(
        "mark_component_healthy",
        RecoveryAdapters.service_host_health_handler(
            host
        ),
    )

    manager = RecoveryManager(
        executor=executor
    )

    plan = manager.recover(report)

    eq(
        plan.actions[0].status,
        "succeeded",
        "service-host recovery action succeeds",
    )

    recovered = host.dispatch(
        ServiceRequest(
            "r2",
            "echo_service",
            "echo",
        )
    )

    eq(
        recovered.success,
        True,
        "recovered hosted instance serves traffic again",
    )

    host.stop()


def test_unknown_host_target_fails_safely():
    host = ServiceHost()
    host.start(1)

    executor = RecoveryExecutor()

    executor.register(
        "mark_component_healthy",
        RecoveryAdapters.service_host_health_handler(
            host
        ),
    )

    action = RecoveryAction(
        "a1",
        "mark_component_healthy",
        "missing",
        "PROBE_UNHEALTHY",
        automatic=True,
    )

    executor.execute(action)

    eq(
        action.status,
        "failed",
        "unknown host recovery target fails",
    )

    host.stop()


def test_worker_bookkeeping_adapter():
    pool = WorkerPool(
        worker_count=1,
        queue_capacity=2,
    )

    pool.start()

    executor = RecoveryExecutor()

    executor.register(
        "clear_transient_failure_state",
        RecoveryAdapters.worker_failure_bookkeeping_handler(
            pool
        ),
    )

    action = RecoveryAction(
        "a1",
        "clear_transient_failure_state",
        "worker_pool",
        "WORKER_TASK_FAILURES",
        automatic=True,
    )

    executor.execute(action)

    eq(
        action.status,
        "succeeded",
        "running worker pool bookkeeping recovery succeeds",
    )

    eq(
        action.result["recovered"],
        True,
        "worker bookkeeping result marks recovered",
    )

    pool.shutdown()


def test_plan_statuses():
    plan = RecoveryPlan(
        "p1",
        "r1",
    )

    a = RecoveryAction(
        "a1",
        "x",
        "t",
        "C",
        automatic=True,
    )

    b = RecoveryAction(
        "a2",
        "y",
        "t",
        "D",
        automatic=False,
    )

    plan.add(a)
    plan.add(b)

    a.mark_running()
    a.mark_succeeded()

    b.mark_skipped(
        "manual"
    )

    eq(
        plan.refresh_status(),
        "partial",
        "mixed success/skipped plan becomes partial",
    )


def test_duplicate_handler():
    executor = RecoveryExecutor()

    executor.register(
        "x",
        lambda action: None,
    )

    expect_error(
        ValueError,
        lambda: executor.register(
            "x",
            lambda action: None,
        ),
        "duplicate recovery handler rejected",
    )


def main():
    test_action_state_machine()
    test_policy_manual_vs_automatic()
    test_manager_builds_plan()
    test_dry_run()
    test_manual_action_not_executed()
    test_service_host_recovery_adapter()
    test_unknown_host_target_fails_safely()
    test_worker_bookkeeping_adapter()
    test_plan_statuses()
    test_duplicate_handler()

    print(
        "RUNTIME RECOVERY TEST SUITE: PASS"
    )
    print(
        "Assertions passed:",
        ASSERTIONS,
    )
    print(
        "Files validated: 6/6"
    )
    print(
        "Diagnostic finding -> recovery plan mapping: VALIDATED"
    )
    print(
        "Automatic/manual recovery boundaries: VALIDATED"
    )
    print(
        "Dry-run safety semantics: VALIDATED"
    )
    print(
        "Allowlisted handler execution: VALIDATED"
    )
    print(
        "ServiceHost health recovery adapter: VALIDATED"
    )
    print(
        "WorkerPool non-restart bookkeeping adapter: VALIDATED"
    )
    print(
        "Third-party dependencies: 0"
    )


main()
