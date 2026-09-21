import os
import shutil
import threading

PROTOCOL_BASE = "libs/protocol/"
LOAD_BALANCER_BASE = "services/load_balancer/"
DISCOVERY_BASE = "services/service_discovery/"
LOGGING_BASE = "services/logging_service/"
METRICS_BASE = "services/metrics_service/"
TRACING_BASE = "services/tracing_service/"

CONCURRENCY_BASE = "runtime/concurrency/"
PROCESSES_BASE = "runtime/processes/"
STORAGE_BASE = "runtime/storage/"
LIFECYCLE_BASE = "runtime/lifecycle/"
BOOTSTRAP_BASE = "runtime/bootstrap/"
HOST_BASE = "runtime/service_host/"
HEALTH_BASE = "runtime/health/"
SIGNALS_BASE = "runtime/signals/"
OBSERVABILITY_BASE = "runtime/observability/"
DIAGNOSTICS_BASE = "runtime/diagnostics/"
RECOVERY_BASE = "runtime/recovery/"
MAINTENANCE_BASE = "runtime/maintenance/"
CONTROL_BASE = "runtime/control_plane/"
COMPOSITION_BASE = "runtime/composition/"
ENTRYPOINT_BASE = "runtime/entrypoint/"

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
        HEALTH_BASE,
        [
            "probe.py",
            "adapters.py",
            "manager.py",
            "monitoring_bridge.py",
        ],
    ),
    (
        SIGNALS_BASE,
        [
            "event.py",
            "coordinator.py",
            "registry.py",
            "handler.py",
            "runtime_bridge.py",
            "lifecycle_adapter.py",
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
        MAINTENANCE_BASE,
        [
            "state.py",
            "snapshot.py",
            "drain.py",
            "manager.py",
            "dispatcher.py",
        ],
    ),
    (
        CONTROL_BASE,
        [
            "result.py",
            "controller.py",
            "service.py",
        ],
    ),
    (
        COMPOSITION_BASE,
        [
            "spec.py",
            "components.py",
            "builder.py",
            "system.py",
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
    "exit_status.py",
    "runner.py",
    "factory.py",
    "main.py",
]:
    path = (
        ENTRYPOINT_BASE
        + filename
    )

    source = open(
        path,
        "r",
        encoding="utf-8",
    ).read()

    if "import " in source:
        raise AssertionError(
            "entrypoint implementation contains forbidden import: "
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
    "runtime/entrypoint/"
    "_test_runtime"
)

FAIL_ROOT = (
    "runtime/entrypoint/"
    "_test_fail"
)


class Clock:
    def __init__(
        self,
        start=100,
    ):
        self.value = start

    def now(
        self,
    ):
        value = self.value
        self.value += 1
        return value


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


def cleanup():
    for path in (
        ROOT,
        FAIL_ROOT,
    ):
        if os.path.exists(
            path
        ):
            shutil.rmtree(
                path
            )


def echo(
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


def make_spec(
    root=ROOT,
):
    clock = Clock()

    return RuntimeSystemSpec(
        storage_root=root,
        time_provider=clock.now,
        worker_count=1,
        queue_capacity=4,
        service_bindings=[
            ServiceBinding(
                "echo-1",
                "echo_service",
                echo,
            ),
        ],
    )


def test_exit_status():
    status = RuntimeExitStatus(
        RuntimeExitStatus.EXIT_OK,
        "ok",
        started=True,
        stopped=True,
    )

    eq(
        status.ok(),
        True,
        "zero runtime exit code is successful",
    )

    eq(
        status.to_dict()[
            "stopped"
        ],
        True,
        "exit status serializes stopped state",
    )


def test_factory():
    factory = RuntimeEntrypointFactory()

    entrypoint = factory.create(
        make_spec()
    )

    check(
        isinstance(
            entrypoint,
            RuntimeEntrypoint,
        ),
        "factory creates RuntimeEntrypoint",
    )

    eq(
        entrypoint.system.status()[
            "running"
        ],
        False,
        "factory does not auto-start system",
    )


def test_shutdown_already_requested():
    entrypoint = (
        RuntimeEntrypointFactory()
        .create(
            make_spec()
        )
    )

    entrypoint.request_shutdown(
        "test shutdown",
        metadata={
            "source": "test",
        },
    )

    status = entrypoint.run()

    eq(
        status.code,
        RuntimeExitStatus.EXIT_OK,
        "pre-requested shutdown exits cleanly",
    )

    eq(
        status.started,
        True,
        "runtime started before clean shutdown",
    )

    eq(
        status.stopped,
        True,
        "runtime stopped after shutdown request",
    )

    eq(
        status.details[
            "shutdown_event"
        ][
            "reason"
        ],
        "test shutdown",
        "shutdown reason preserved",
    )


def test_wait_then_external_shutdown():
    entrypoint = (
        RuntimeEntrypointFactory()
        .create(
            make_spec()
        )
    )

    result = []

    thread = threading.Thread(
        target=lambda: result.append(
            entrypoint.run(
                wait_timeout=3.0
            )
        )
    )

    thread.start()

    coordinator = (
        entrypoint.system
        .components
        .get(
            "shutdown_coordinator"
        )
    )

    check(
        coordinator.wait(
            timeout=0.05
        )
        is False,
        "entrypoint is waiting for shutdown",
    )

    entrypoint.request_shutdown(
        "external request"
    )

    thread.join(
        timeout=4.0
    )

    eq(
        len(
            result
        ),
        1,
        "entrypoint thread completed",
    )

    eq(
        result[
            0
        ].code,
        RuntimeExitStatus.EXIT_OK,
        "external shutdown exits cleanly",
    )


def test_wait_timeout_stops_runtime():
    entrypoint = (
        RuntimeEntrypointFactory()
        .create(
            make_spec()
        )
    )

    status = entrypoint.run(
        wait_timeout=0.01
    )

    eq(
        status.code,
        RuntimeExitStatus.EXIT_WAIT_TIMEOUT,
        "wait timeout gets dedicated exit code",
    )

    eq(
        status.stopped,
        True,
        "timeout path still stops runtime cleanly",
    )


def test_startup_failure():
    bad_spec = RuntimeSystemSpec(
        storage_root=FAIL_ROOT,
        time_provider=(
            Clock().now
        ),
        worker_count=1,
        queue_capacity=2,
        process_specs=[
            ProcessSpec(
                "broken",
                [
                    "definitely-not-a-real-sirellm-program-xyz",
                ],
            ),
        ],
    )

    entrypoint = (
        RuntimeEntrypointFactory()
        .create(
            bad_spec
        )
    )

    status = entrypoint.run(
        wait_timeout=0.01
    )

    eq(
        status.code,
        RuntimeExitStatus.EXIT_STARTUP_FAILED,
        "startup failure gets stable exit code",
    )

    eq(
        status.started,
        False,
        "failed startup not reported as started",
    )

    check(
        len(
            status.details[
                "error_type"
            ]
        ) > 0,
        "startup error type retained",
    )


def test_programmatic_main():
    spec = make_spec()

    system = (
        RuntimeCompositionBuilder()
        .build(
            spec
        )
    )

    coordinator = (
        system.components
        .get(
            "shutdown_coordinator"
        )
    )

    coordinator.request(
        "main test"
    )

    runner = RuntimeEntrypoint(
        system
    )

    status = runner.run()

    eq(
        status.code,
        RuntimeExitStatus.EXIT_OK,
        "programmatic entrypoint semantics validated",
    )


def test_invalid_timeout():
    entrypoint = (
        RuntimeEntrypointFactory()
        .create(
            make_spec()
        )
    )

    expect_error(
        ValueError,
        lambda: entrypoint.run(
            wait_timeout=-1
        ),
        "negative wait timeout rejected",
    )


def test_runner_status():
    entrypoint = (
        RuntimeEntrypointFactory()
        .create(
            make_spec()
        )
    )

    entrypoint.request_shutdown(
        "status test"
    )

    result = entrypoint.run()

    public = entrypoint.status()

    eq(
        public[
            "run_count"
        ],
        1,
        "entrypoint run count tracked",
    )

    eq(
        public[
            "last_status"
        ][
            "code"
        ],
        result.code,
        "entrypoint retains last exit status",
    )


def main():
    try:
        test_exit_status()
        test_factory()
        test_shutdown_already_requested()
        test_wait_then_external_shutdown()
        test_wait_timeout_stops_runtime()
        test_startup_failure()
        test_programmatic_main()
        test_invalid_timeout()
        test_runner_status()

    finally:
        cleanup()

    print(
        "RUNTIME ENTRYPOINT TEST SUITE: PASS"
    )
    print(
        "Assertions passed:",
        ASSERTIONS,
    )
    print(
        "Files validated: 4/4"
    )
    print(
        "Composition-root entrypoint factory: VALIDATED"
    )
    print(
        "Startup + shutdown lifecycle execution: VALIDATED"
    )
    print(
        "External shutdown coordination: VALIDATED"
    )
    print(
        "Wait-timeout cleanup path: VALIDATED"
    )
    print(
        "Stable runtime exit codes: VALIDATED"
    )
    print(
        "Startup failure reporting: VALIDATED"
    )
    print(
        "Third-party dependencies: 0"
    )
    print(
        "Test-only concurrency dependency: threading"
    )


main()
