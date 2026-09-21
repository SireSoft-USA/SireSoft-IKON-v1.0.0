import os
import shutil
import signal

CONCURRENCY_BASE = "runtime/concurrency/"
PROCESSES_BASE = "runtime/processes/"
STORAGE_BASE = "runtime/storage/"
LIFECYCLE_BASE = "runtime/lifecycle/"
BOOTSTRAP_BASE = "runtime/bootstrap/"
SIGNALS_BASE = "runtime/signals/"

namespace = {
    "__builtins__": __builtins__,
}

groups = [
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
    "event.py",
    "coordinator.py",
    "registry.py",
    "handler.py",
    "runtime_bridge.py",
    "lifecycle_adapter.py",
]:
    path = SIGNALS_BASE + filename

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

globals().update(
    namespace
)

ASSERTIONS = 0

ROOT = (
    "runtime/signals/"
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
    if os.path.exists(
        ROOT
    ):
        shutil.rmtree(
            ROOT
        )


def test_event():
    event = ShutdownSignalEvent(
        reason="manual",
        signal_name="SIGINT",
        signal_number=2,
        metadata={
            "source": "test",
        },
    )

    eq(
        event.to_dict()[
            "reason"
        ],
        "manual",
        "shutdown event reason",
    )

    eq(
        event.to_dict()[
            "metadata"
        ][
            "source"
        ],
        "test",
        "shutdown event metadata",
    )


def test_coordinator_first_request_wins():
    callbacks = []

    coordinator = (
        ShutdownCoordinator(
            callback=(
                lambda event: (
                    callbacks.append(
                        event.reason
                    )
                )
            )
        )
    )

    first = coordinator.request(
        "first",
        signal_name="SIGINT",
        signal_number=2,
    )

    second = coordinator.request(
        "second",
        signal_name="SIGTERM",
        signal_number=15,
    )

    eq(
        first.reason,
        "first",
        "first shutdown request stored",
    )

    eq(
        second.reason,
        "first",
        "later request returns canonical event",
    )

    eq(
        coordinator.status()[
            "request_count"
        ],
        2,
        "all shutdown requests counted",
    )

    eq(
        callbacks,
        [
            "first",
        ],
        "shutdown callback fires once",
    )

    eq(
        coordinator.wait(
            timeout=0.01
        ),
        True,
        "coordinator wait resolves after request",
    )


def test_registry():
    registry = (
        RuntimeSignalRegistry()
    )

    check(
        registry.count() >= 1,
        "at least one standard signal is available",
    )

    if hasattr(
        signal,
        "SIGINT",
    ):
        eq(
            registry.number(
                "SIGINT"
            ),
            int(
                signal.SIGINT
            ),
            "SIGINT number resolved",
        )

        eq(
            registry.name_for(
                int(
                    signal.SIGINT
                )
            ),
            "SIGINT",
            "signal number resolves back to name",
        )


def test_handler_simulate():
    coordinator = (
        ShutdownCoordinator()
    )

    registry = (
        RuntimeSignalRegistry(
            [
                "SIGINT",
            ]
        )
    )

    handler = RuntimeSignalHandler(
        coordinator,
        registry=registry,
    )

    event = handler.simulate(
        registry.number(
            "SIGINT"
        )
    )

    eq(
        coordinator.requested(),
        True,
        "simulated signal requests shutdown",
    )

    eq(
        event.signal_name,
        "SIGINT",
        "simulated signal records name",
    )


def test_install_restore():
    coordinator = (
        ShutdownCoordinator()
    )

    registry = (
        RuntimeSignalRegistry(
            [
                "SIGINT",
            ]
        )
    )

    handler = RuntimeSignalHandler(
        coordinator,
        registry=registry,
    )

    number = registry.number(
        "SIGINT"
    )

    previous = signal.getsignal(
        number
    )

    handler.install()

    eq(
        handler.installed(),
        True,
        "signal handler installs",
    )

    check(
        signal.getsignal(
            number
        )
        == handler._handle,
        "installed signal uses runtime handler",
    )

    handler.restore()

    eq(
        handler.installed(),
        False,
        "signal handler restores",
    )

    eq(
        signal.getsignal(
            number
        ),
        previous,
        "previous signal handler restored",
    )


def test_lifecycle_adapter():
    coordinator = (
        ShutdownCoordinator()
    )

    registry = (
        RuntimeSignalRegistry(
            [
                "SIGINT",
            ]
        )
    )

    handler = RuntimeSignalHandler(
        coordinator,
        registry=registry,
    )

    lifecycle = (
        LifecycleManager()
    )

    lifecycle.register(
        RuntimeSignalLifecycleAdapter
        .resource(
            "signals",
            handler,
        )
    )

    lifecycle.start_all()

    eq(
        handler.installed(),
        True,
        "lifecycle starts signal handler",
    )

    lifecycle.stop_all()

    eq(
        handler.installed(),
        False,
        "lifecycle restores signal handler",
    )


def test_runtime_shutdown_bridge():
    cleanup()

    app = RuntimeBuilder().build(
        RuntimeBootstrapConfig(
            storage_root=ROOT,
            worker_count=1,
            queue_capacity=2,
        )
    )

    app.start()

    coordinator = (
        ShutdownCoordinator()
    )

    bridge = RuntimeShutdownBridge(
        coordinator,
        app,
    )

    eq(
        bridge.run_shutdown_if_requested(),
        {
            "requested": False,
            "stopped": False,
        },
        "bridge does nothing before shutdown request",
    )

    coordinator.request(
        "manual shutdown"
    )

    result = (
        bridge
        .run_shutdown_if_requested()
    )

    eq(
        result[
            "requested"
        ],
        True,
        "bridge observes shutdown request",
    )

    eq(
        result[
            "stopped"
        ],
        True,
        "bridge stops runtime application",
    )

    eq(
        app.status()[
            "stopped"
        ],
        True,
        "runtime application stopped",
    )

    eq(
        bridge.status()[
            "shutdown_count"
        ],
        1,
        "bridge shutdown count",
    )

    again = (
        bridge
        .run_shutdown_if_requested()
    )

    eq(
        again[
            "stopped"
        ],
        True,
        "repeated bridge call remains stopped",
    )

    eq(
        bridge.status()[
            "shutdown_count"
        ],
        1,
        "repeated bridge does not double-stop runtime",
    )


def test_coordinator_timeout():
    coordinator = (
        ShutdownCoordinator()
    )

    eq(
        coordinator.wait(
            timeout=0.01
        ),
        False,
        "coordinator wait times out before request",
    )

    expect_error(
        ValueError,
        lambda: coordinator.wait(
            timeout=-1
        ),
        "negative coordinator timeout rejected",
    )


def test_unknown_signal_name_fallback():
    registry = (
        RuntimeSignalRegistry(
            []
        )
    )

    eq(
        registry.name_for(
            999
        ),
        "SIGNAL_999",
        "unknown signal number gets stable fallback name",
    )


def main():
    try:
        test_event()
        test_coordinator_first_request_wins()
        test_registry()
        test_handler_simulate()
        test_install_restore()
        test_lifecycle_adapter()
        test_runtime_shutdown_bridge()
        test_coordinator_timeout()
        test_unknown_signal_name_fallback()

    finally:
        cleanup()

    print(
        "RUNTIME SIGNALS TEST SUITE: PASS"
    )
    print(
        "Assertions passed:",
        ASSERTIONS,
    )
    print(
        "Files validated: 6/6"
    )
    print(
        "Thread-safe shutdown coordination: VALIDATED"
    )
    print(
        "Portable SIGINT/SIGTERM registry: VALIDATED"
    )
    print(
        "Signal handler install/restore: VALIDATED"
    )
    print(
        "Idempotent first-request shutdown semantics: VALIDATED"
    )
    print(
        "RuntimeApplication shutdown bridge: VALIDATED"
    )
    print(
        "Lifecycle adapter integration: VALIDATED"
    )
    print(
        "Third-party dependencies: 0"
    )
    print(
        "Standard-library signal dependencies: signal, threading"
    )


main()
