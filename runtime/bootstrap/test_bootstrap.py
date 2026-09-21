import os
import shutil
import sys

CONCURRENCY_BASE = "runtime/concurrency/"
PROCESSES_BASE = "runtime/processes/"
STORAGE_BASE = "runtime/storage/"
LIFECYCLE_BASE = "runtime/lifecycle/"
BOOTSTRAP_BASE = "runtime/bootstrap/"

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
    "config.py",
    "context.py",
    "application.py",
    "builder.py",
]:
    path = BOOTSTRAP_BASE + filename

    source = open(
        path,
        "r",
        encoding="utf-8",
    ).read()

    if "import " in source:
        raise AssertionError(
            "bootstrap implementation contains forbidden import: "
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
    "runtime/bootstrap/"
    "_test_runtime"
)

FAIL_ROOT = (
    "runtime/bootstrap/"
    "_test_runtime_failure"
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
    for path in (
        ROOT,
        FAIL_ROOT,
    ):
        if os.path.exists(path):
            shutil.rmtree(path)


def test_config():
    config = RuntimeBootstrapConfig(
        storage_root=ROOT,
        worker_count=2,
        queue_capacity=8,
        storage_namespaces=[
            "runtime",
            "cache",
            "runtime",
        ],
        metadata={
            "environment": "test",
        },
    )

    eq(
        config.storage_namespaces,
        [
            "runtime",
            "cache",
        ],
        "bootstrap config deduplicates namespaces",
    )

    eq(
        config.public_dict()[
            "worker_count"
        ],
        2,
        "bootstrap config public worker count",
    )

    expect_error(
        ValueError,
        lambda: RuntimeBootstrapConfig(
            storage_root=ROOT,
            worker_count=0,
        ),
        "invalid worker count rejected",
    )


def test_context():
    context = RuntimeContext()

    context.register(
        "a",
        1,
    )
    context.register(
        "b",
        2,
    )

    eq(
        context.names(),
        [
            "a",
            "b",
        ],
        "context preserves registration order",
    )

    eq(
        context.get(
            "b"
        ),
        2,
        "context retrieves registered value",
    )

    context.seal()

    expect_error(
        RuntimeError,
        lambda: context.register(
            "c",
            3,
        ),
        "sealed context rejects mutation",
    )


def test_build_not_started():
    cleanup()

    app = RuntimeBuilder().build(
        RuntimeBootstrapConfig(
            storage_root=ROOT,
            worker_count=2,
            queue_capacity=4,
            storage_namespaces=[
                "runtime",
                "cache",
            ],
        )
    )

    status = app.status()

    eq(
        status["running"],
        False,
        "build does not automatically start runtime",
    )

    eq(
        status["worker_pool"][
            "started"
        ],
        False,
        "worker pool remains stopped after build",
    )

    eq(
        status["context"][
            "sealed"
        ],
        True,
        "runtime context sealed after build",
    )


def test_start_submit_storage_stop():
    cleanup()

    app = RuntimeBuilder().build(
        RuntimeBootstrapConfig(
            storage_root=ROOT,
            worker_count=2,
            queue_capacity=4,
            storage_namespaces=[
                "runtime",
                "cache",
            ],
        )
    )

    started = app.start()

    eq(
        started["running"],
        True,
        "runtime application starts",
    )

    eq(
        started["lifecycle"][
            "last_start_order"
        ],
        [
            "storage",
            "workers",
        ],
        "bootstrap lifecycle dependency order",
    )

    eq(
        [
            row["name"]
            for row
            in app.storage()
            .list_namespaces()
        ],
        [
            "runtime",
            "cache",
        ],
        "bootstrap creates configured storage namespaces",
    )

    future = app.submit(
        lambda left, right: (
            left
            + right
        ),
        20,
        22,
    )

    eq(
        future.result(
            timeout=2.0
        ),
        42,
        "bootstrapped worker pool executes submitted task",
    )

    app.storage().put(
        "runtime",
        "state",
        b"ready",
    )

    eq(
        app.storage().get(
            "runtime",
            "state",
        ),
        b"ready",
        "bootstrapped storage usable",
    )

    stopped = app.stop()

    eq(
        stopped["stopped"],
        True,
        "runtime application stops",
    )

    eq(
        stopped["lifecycle"][
            "last_stop_order"
        ],
        [
            "workers",
            "storage",
        ],
        "bootstrap shutdown reverse order",
    )

    expect_error(
        RuntimeError,
        lambda: app.submit(
            lambda: None
        ),
        "stopped runtime rejects task submission",
    )


def test_process_integration():
    cleanup()

    spec = ProcessSpec(
        name="background",
        command=[
            sys.executable,
            "-S",
            "-c",
            (
                "import time; "
                "time.sleep(30)"
            ),
        ],
    )

    app = RuntimeBuilder().build(
        RuntimeBootstrapConfig(
            storage_root=ROOT,
            worker_count=1,
            queue_capacity=2,
            process_specs=[
                spec,
            ],
            process_shutdown_timeout=1.0,
        )
    )

    app.start()

    process = (
        app.process_supervisor()
        .registry
        .get_process(
            "background"
        )
    )

    check(
        process.running(),
        "bootstrap starts configured child process",
    )

    eq(
        app.status()["lifecycle"][
            "last_start_order"
        ],
        [
            "storage",
            "workers",
            "processes",
        ],
        "process resource starts after workers",
    )

    app.stop()

    eq(
        process.running(),
        False,
        "bootstrap stops configured child process",
    )


def test_start_failure_rolls_back_workers():
    cleanup()

    bad = ProcessSpec(
        name="broken",
        command=[
            (
                "definitely-not-a-real-"
                "sirellm-executable-xyz"
            ),
        ],
    )

    app = RuntimeBuilder().build(
        RuntimeBootstrapConfig(
            storage_root=FAIL_ROOT,
            worker_count=1,
            queue_capacity=2,
            process_specs=[
                bad,
            ],
        )
    )

    expect_error(
        OSError,
        lambda: app.start(),
        "process startup failure propagated",
    )

    status = app.status()

    eq(
        status["lifecycle"][
            "phase"
        ],
        "failed",
        "bootstrap lifecycle reports failed startup",
    )

    eq(
        status["worker_pool"][
            "shutdown"
        ],
        True,
        "failed process startup rolls back worker pool",
    )

    eq(
        status["lifecycle"][
            "total_rollbacks"
        ],
        1,
        "failed bootstrap records rollback",
    )


def test_restart_after_stop_rejected():
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

    expect_error(
        RuntimeError,
        lambda: app.start(),
        "single-start runtime does not attempt invalid WorkerPool restart",
    )


def test_duplicate_process_specs():
    spec_one = ProcessSpec(
        "same",
        [
            sys.executable,
            "-S",
            "-c",
            "pass",
        ],
    )

    spec_two = ProcessSpec(
        "same",
        [
            sys.executable,
            "-S",
            "-c",
            "pass",
        ],
    )

    expect_error(
        ValueError,
        lambda: RuntimeBootstrapConfig(
            storage_root=ROOT,
            process_specs=[
                spec_one,
                spec_two,
            ],
        ),
        "duplicate process names rejected in config",
    )


def test_status_shape():
    cleanup()

    app = RuntimeBuilder().build(
        RuntimeBootstrapConfig(
            storage_root=ROOT,
            worker_count=1,
            queue_capacity=2,
        )
    )

    app.start()

    status = app.status()

    eq(
        status["context"][
            "names"
        ],
        [
            "config",
            "storage",
            "worker_pool",
            "process_supervisor",
            "lifecycle",
        ],
        "bootstrap context exposes expected core runtime objects",
    )

    eq(
        status["lifecycle"][
            "ready"
        ],
        True,
        "lifecycle ready after bootstrap start",
    )

    app.stop()


def main():
    try:
        test_config()
        test_context()
        test_build_not_started()
        test_start_submit_storage_stop()
        test_process_integration()
        test_start_failure_rolls_back_workers()
        test_restart_after_stop_rejected()
        test_duplicate_process_specs()
        test_status_shape()

    finally:
        cleanup()

    print(
        "RUNTIME BOOTSTRAP TEST SUITE: PASS"
    )
    print(
        "Assertions passed:",
        ASSERTIONS,
    )
    print(
        "Files validated: 4/4"
    )
    print(
        "Explicit runtime bootstrap configuration: VALIDATED"
    )
    print(
        "Sealed runtime context: VALIDATED"
    )
    print(
        "RuntimeStorage + WorkerPool construction: VALIDATED"
    )
    print(
        "ProcessSupervisor construction/integration: VALIDATED"
    )
    print(
        "Lifecycle-ordered startup/shutdown: VALIDATED"
    )
    print(
        "Startup failure rollback: VALIDATED"
    )
    print(
        "Third-party dependencies: 0"
    )


main()
