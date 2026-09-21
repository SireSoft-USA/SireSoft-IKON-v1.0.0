import os
import shutil
import sys

PROTOCOL_BASE = "libs/protocol/"
NETWORK_BASE = "runtime/networking/"
CONCURRENCY_BASE = "runtime/concurrency/"
PROCESSES_BASE = "runtime/processes/"
STORAGE_BASE = "runtime/storage/"
LIFECYCLE_BASE = "runtime/lifecycle/"

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
            "validator.py",
            "codec.py",
        ],
    ),
    (
        NETWORK_BASE,
        [
            "http_parser.py",
            "tcp_server.py",
            "tcp_client.py",
            "connection_pool.py",
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
    "resource.py",
    "graph.py",
    "manager.py",
    "adapters.py",
]:
    path = LIFECYCLE_BASE + filename

    source = open(
        path,
        "r",
        encoding="utf-8",
    ).read()

    if "import " in source:
        raise AssertionError(
            "lifecycle implementation contains forbidden import: "
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
    "runtime/lifecycle/"
    "_test_storage"
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


def test_graph_order():
    graph = LifecycleGraph()

    graph.add(
        LifecycleResource(
            "storage",
            lambda: None,
            lambda: None,
        )
    )

    graph.add(
        LifecycleResource(
            "workers",
            lambda: None,
            lambda: None,
            dependencies=[
                "storage",
            ],
        )
    )

    graph.add(
        LifecycleResource(
            "api",
            lambda: None,
            lambda: None,
            dependencies=[
                "workers",
            ],
        )
    )

    eq(
        graph.resolve_order(),
        [
            "storage",
            "workers",
            "api",
        ],
        "dependency startup order",
    )

    eq(
        graph.reverse_order(),
        [
            "api",
            "workers",
            "storage",
        ],
        "dependency shutdown order",
    )


def test_cycle_detection():
    graph = LifecycleGraph()

    graph.add(
        LifecycleResource(
            "a",
            lambda: None,
            lambda: None,
            dependencies=[
                "b",
            ],
        )
    )

    graph.add(
        LifecycleResource(
            "b",
            lambda: None,
            lambda: None,
            dependencies=[
                "a",
            ],
        )
    )

    expect_error(
        ValueError,
        lambda: graph.resolve_order(),
        "dependency cycle rejected",
    )


def test_missing_dependency():
    graph = LifecycleGraph()

    graph.add(
        LifecycleResource(
            "api",
            lambda: None,
            lambda: None,
            dependencies=[
                "workers",
            ],
        )
    )

    expect_error(
        ValueError,
        lambda: graph.validate(),
        "missing dependency rejected",
    )


def test_start_stop_order():
    events = []

    manager = LifecycleManager()

    manager.register(
        LifecycleResource(
            "storage",
            lambda: events.append(
                "start:storage"
            ),
            lambda: events.append(
                "stop:storage"
            ),
        )
    )

    manager.register(
        LifecycleResource(
            "workers",
            lambda: events.append(
                "start:workers"
            ),
            lambda: events.append(
                "stop:workers"
            ),
            dependencies=[
                "storage",
            ],
        )
    )

    manager.register(
        LifecycleResource(
            "gateway",
            lambda: events.append(
                "start:gateway"
            ),
            lambda: events.append(
                "stop:gateway"
            ),
            dependencies=[
                "workers",
            ],
        )
    )

    eq(
        manager.start_all(),
        [
            "storage",
            "workers",
            "gateway",
        ],
        "manager starts in dependency order",
    )

    eq(
        manager.status()[
            "phase"
        ],
        "running",
        "manager enters running phase",
    )

    eq(
        manager.stop_all(),
        [
            "gateway",
            "workers",
            "storage",
        ],
        "manager stops in reverse dependency order",
    )

    eq(
        events,
        [
            "start:storage",
            "start:workers",
            "start:gateway",
            "stop:gateway",
            "stop:workers",
            "stop:storage",
        ],
        "callbacks execute in expected order",
    )


def test_start_rollback():
    events = []

    manager = LifecycleManager()

    manager.register(
        LifecycleResource(
            "storage",
            lambda: events.append(
                "start:storage"
            ),
            lambda: events.append(
                "stop:storage"
            ),
        )
    )

    def fail_start():
        events.append(
            "start:workers"
        )

        raise RuntimeError(
            "worker startup failed"
        )

    manager.register(
        LifecycleResource(
            "workers",
            fail_start,
            lambda: events.append(
                "stop:workers"
            ),
            dependencies=[
                "storage",
            ],
        )
    )

    expect_error(
        RuntimeError,
        lambda: manager.start_all(),
        "startup failure propagated",
    )

    eq(
        events,
        [
            "start:storage",
            "start:workers",
            "stop:storage",
        ],
        "successful resources rolled back in reverse order",
    )

    eq(
        manager.status()[
            "total_rollbacks"
        ],
        1,
        "rollback count tracked",
    )

    eq(
        manager.status()[
            "phase"
        ],
        "failed",
        "manager enters failed phase after startup failure",
    )


def test_worker_pool_adapter():
    pool = WorkerPool(
        worker_count=2,
        queue_capacity=4,
    )

    resource = (
        WorkerPoolLifecycleAdapter
        .resource(
            "workers",
            pool,
        )
    )

    manager = LifecycleManager()
    manager.register(
        resource
    )

    manager.start_all()

    eq(
        pool.status()[
            "started"
        ],
        True,
        "worker pool lifecycle starts pool",
    )

    future = pool.submit(
        lambda: 42
    )

    eq(
        future.result(
            timeout=2.0
        ),
        42,
        "started worker pool executes tasks",
    )

    manager.stop_all()

    eq(
        pool.status()[
            "shutdown"
        ],
        True,
        "worker pool lifecycle shuts pool down",
    )


def test_storage_adapter():
    if os.path.exists(
        ROOT
    ):
        shutil.rmtree(
            ROOT
        )

    storage = RuntimeStorage(
        ROOT
    )

    resource = (
        StorageLifecycleAdapter
        .resource(
            "storage",
            storage,
            namespaces=[
                "runtime",
                "cache",
            ],
        )
    )

    manager = LifecycleManager()
    manager.register(
        resource
    )

    manager.start_all()

    eq(
        [
            row[
                "name"
            ]
            for row
            in storage.list_namespaces()
        ],
        [
            "runtime",
            "cache",
        ],
        "storage lifecycle creates namespaces",
    )

    manager.stop_all()


def test_process_supervisor_adapter():
    supervisor = ProcessSupervisor()

    supervisor.register(
        ProcessSpec(
            name="child",
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
    )

    resource = (
        ProcessSupervisorLifecycleAdapter
        .resource(
            "processes",
            supervisor,
            [
                "child",
            ],
            timeout=1.0,
        )
    )

    manager = LifecycleManager()
    manager.register(
        resource
    )

    manager.start_all()

    check(
        supervisor.registry
        .get_process(
            "child"
        )
        .running(),
        "process lifecycle starts registered child",
    )

    manager.stop_all()

    eq(
        supervisor.registry
        .get_process(
            "child"
        )
        .running(),
        False,
        "process lifecycle stops child",
    )


def test_integrated_runtime_order():
    if os.path.exists(
        ROOT
    ):
        shutil.rmtree(
            ROOT
        )

    storage = RuntimeStorage(
        ROOT
    )

    pool = WorkerPool(
        worker_count=1,
        queue_capacity=4,
    )

    supervisor = ProcessSupervisor()

    supervisor.register(
        ProcessSpec(
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
    )

    manager = LifecycleManager()

    manager.register(
        StorageLifecycleAdapter
        .resource(
            "storage",
            storage,
            namespaces=[
                "runtime",
            ],
        )
    )

    manager.register(
        WorkerPoolLifecycleAdapter
        .resource(
            "workers",
            pool,
            dependencies=[
                "storage",
            ],
        )
    )

    manager.register(
        ProcessSupervisorLifecycleAdapter
        .resource(
            "processes",
            supervisor,
            [
                "background",
            ],
            dependencies=[
                "workers",
            ],
            timeout=1.0,
        )
    )

    eq(
        manager.start_all(),
        [
            "storage",
            "workers",
            "processes",
        ],
        "real runtime components start in dependency order",
    )

    status = manager.status()

    eq(
        status[
            "ready"
        ],
        True,
        "integrated runtime lifecycle ready",
    )

    eq(
        status[
            "running_resources"
        ],
        3,
        "all integrated runtime resources running",
    )

    eq(
        manager.stop_all(),
        [
            "processes",
            "workers",
            "storage",
        ],
        "real runtime components stop in reverse order",
    )


def test_idempotent_running_start():
    manager = LifecycleManager()
    count = {
        "starts": 0,
    }

    def start():
        count[
            "starts"
        ] += 1

    manager.register(
        LifecycleResource(
            "x",
            start,
            lambda: None,
        )
    )

    first = manager.start_all()
    second = manager.start_all()

    eq(
        first,
        [
            "x",
        ],
        "first startup",
    )

    eq(
        second,
        [
            "x",
        ],
        "running startup returns existing order",
    )

    eq(
        count[
            "starts"
        ],
        1,
        "running lifecycle does not double-start resource",
    )

    manager.stop_all()


def test_resource_validation():
    expect_error(
        ValueError,
        lambda: LifecycleResource(
            "",
            lambda: None,
            lambda: None,
        ),
        "empty resource name rejected",
    )

    expect_error(
        TypeError,
        lambda: LifecycleResource(
            "x",
            None,
            lambda: None,
        ),
        "non-callable start rejected",
    )

    expect_error(
        ValueError,
        lambda: LifecycleResource(
            "x",
            lambda: None,
            lambda: None,
            dependencies=[
                "x",
            ],
        ),
        "self-dependency rejected",
    )


def main():
    try:
        test_graph_order()
        test_cycle_detection()
        test_missing_dependency()
        test_start_stop_order()
        test_start_rollback()
        test_worker_pool_adapter()
        test_storage_adapter()
        test_process_supervisor_adapter()
        test_integrated_runtime_order()
        test_idempotent_running_start()
        test_resource_validation()

    finally:
        if os.path.exists(
            ROOT
        ):
            shutil.rmtree(
                ROOT
            )

    print(
        "RUNTIME LIFECYCLE TEST SUITE: PASS"
    )
    print(
        "Assertions passed:",
        ASSERTIONS,
    )
    print(
        "Files validated: 4/4"
    )
    print(
        "Dependency graph/cycle detection: VALIDATED"
    )
    print(
        "Ordered startup/reverse shutdown: VALIDATED"
    )
    print(
        "Transactional startup rollback: VALIDATED"
    )
    print(
        "WorkerPool lifecycle integration: VALIDATED"
    )
    print(
        "ProcessSupervisor lifecycle integration: VALIDATED"
    )
    print(
        "RuntimeStorage lifecycle integration: VALIDATED"
    )
    print(
        "Third-party dependencies: 0"
    )


main()
