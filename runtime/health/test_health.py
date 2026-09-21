import os
import shutil
import sys

PROTOCOL_BASE = "libs/protocol/"
LOAD_BALANCER_BASE = "services/load_balancer/"
DISCOVERY_BASE = "services/service_discovery/"
CONCURRENCY_BASE = "runtime/concurrency/"
PROCESSES_BASE = "runtime/processes/"
STORAGE_BASE = "runtime/storage/"
LIFECYCLE_BASE = "runtime/lifecycle/"
HOST_BASE = "runtime/service_host/"
HEALTH_BASE = "runtime/health/"

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
        HOST_BASE,
        [
            "binding.py",
            "registry.py",
            "host.py",
            "gateway_dispatcher.py",
            "lifecycle_adapter.py",
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
    "probe.py",
    "adapters.py",
    "manager.py",
    "monitoring_bridge.py",
]:
    path = HEALTH_BASE + filename

    source = open(
        path,
        "r",
        encoding="utf-8",
    ).read()

    if "import " in source:
        raise AssertionError(
            "runtime health implementation contains forbidden import: "
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
    "runtime/health/"
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


class EchoService:
    def handle(
        self,
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


def cleanup():
    if os.path.exists(
        ROOT
    ):
        shutil.rmtree(
            ROOT
        )


def test_probe_result():
    result = RuntimeProbeResult(
        "x",
        "healthy",
        True,
        details={
            "a": 1,
        },
    )

    eq(
        result.to_dict()[
            "status"
        ],
        "healthy",
        "probe result status",
    )

    expect_error(
        ValueError,
        lambda: RuntimeProbeResult(
            "x",
            "unknown",
            True,
        ),
        "invalid probe status rejected",
    )


def test_probe_exception():
    probe = RuntimeProbe(
        "failing",
        lambda: (
            1 / 0
        ),
    )

    result = probe.execute()

    eq(
        result.status,
        "unhealthy",
        "probe exception becomes unhealthy result",
    )

    eq(
        result.ready,
        False,
        "probe exception is not ready",
    )


def test_manager_aggregation():
    manager = (
        RuntimeHealthManager()
    )

    manager.register(
        RuntimeProbe(
            "required",
            lambda: {
                "status": (
                    "healthy"
                ),
                "ready": True,
            },
            required=True,
        )
    )

    manager.register(
        RuntimeProbe(
            "optional",
            lambda: {
                "status": (
                    "unhealthy"
                ),
                "ready": False,
            },
            required=False,
        )
    )

    health = manager.check()

    eq(
        health[
            "status"
        ],
        "degraded",
        "optional unhealthy probe degrades aggregate",
    )

    eq(
        health[
            "ready"
        ],
        True,
        "optional unhealthy probe does not remove readiness",
    )

    eq(
        health[
            "live"
        ],
        True,
        "optional unhealthy probe keeps liveness",
    )


def test_required_failure():
    manager = (
        RuntimeHealthManager()
    )

    manager.register(
        RuntimeProbe(
            "required",
            lambda: {
                "status": (
                    "unhealthy"
                ),
                "ready": False,
            },
            required=True,
        )
    )

    health = manager.check()

    eq(
        health[
            "status"
        ],
        "unhealthy",
        "required unhealthy probe makes aggregate unhealthy",
    )

    eq(
        health[
            "ready"
        ],
        False,
        "required unhealthy probe removes readiness",
    )

    eq(
        health[
            "live"
        ],
        False,
        "required unhealthy probe removes liveness",
    )


def test_real_runtime_adapters():
    cleanup()

    storage = RuntimeStorage(
        ROOT
    )

    pool = WorkerPool(
        worker_count=1,
        queue_capacity=2,
    )

    lifecycle = (
        LifecycleManager()
    )

    lifecycle.register(
        StorageLifecycleAdapter
        .resource(
            "storage",
            storage,
            namespaces=[
                "runtime",
            ],
        )
    )

    lifecycle.register(
        WorkerPoolLifecycleAdapter
        .resource(
            "workers",
            pool,
            dependencies=[
                "storage",
            ],
        )
    )

    lifecycle.start_all()

    manager = (
        RuntimeHealthManager()
    )

    manager.register(
        RuntimeHealthAdapters
        .lifecycle(
            lifecycle
        )
    )

    manager.register(
        RuntimeHealthAdapters
        .worker_pool(
            pool
        )
    )

    manager.register(
        RuntimeHealthAdapters
        .storage(
            storage
        )
    )

    health = manager.check()

    eq(
        health[
            "status"
        ],
        "healthy",
        "running lifecycle/worker/storage runtime is healthy",
    )

    eq(
        health[
            "ready"
        ],
        True,
        "running runtime is ready",
    )

    lifecycle.stop_all()

    after = manager.check()

    eq(
        after[
            "status"
        ],
        "unhealthy",
        "stopped worker pool makes required runtime unhealthy",
    )

    eq(
        after[
            "ready"
        ],
        False,
        "stopped runtime not ready",
    )


def test_service_host_adapter():
    host = ServiceHost()

    host.add_service(
        "echo-1",
        "echo_service",
        EchoService(),
        lease_seconds=5,
    )

    host.start(
        10
    )

    probe = RuntimeHealthAdapters.service_host(
        host,
        lambda: 11,
    )

    healthy = probe.execute()

    eq(
        healthy.status,
        "healthy",
        "healthy service host probe",
    )

    host.sweep_stale(
        15
    )

    unhealthy = (
        RuntimeHealthAdapters
        .service_host(
            host,
            lambda: 15,
        )
        .execute()
    )

    eq(
        unhealthy.status,
        "unhealthy",
        "stale-only service host becomes unhealthy",
    )

    eq(
        unhealthy.ready,
        False,
        "stale-only service host not ready",
    )

    host.stop()


def test_process_supervisor_adapter():
    supervisor = ProcessSupervisor()

    healthy_probe = (
        RuntimeHealthAdapters
        .process_supervisor(
            supervisor
        )
    )

    eq(
        healthy_probe.execute()
        .status,
        "healthy",
        "empty process supervisor is healthy",
    )

    supervisor.register(
        ProcessSpec(
            "fail",
            [
                sys.executable,
                "-S",
                "-c",
                (
                    "import sys; "
                    "sys.exit(3)"
                ),
            ],
        )
    )

    supervisor.start(
        "fail"
    )

    supervisor.wait(
        "fail",
        timeout=3.0,
    )

    result = (
        RuntimeHealthAdapters
        .process_supervisor(
            supervisor
        )
        .execute()
    )

    eq(
        result.status,
        "unhealthy",
        "failed supervised process becomes unhealthy",
    )


def test_monitoring_bridge():
    manager = (
        RuntimeHealthManager()
    )

    manager.register(
        RuntimeProbe(
            "a",
            lambda: {
                "status": (
                    "healthy"
                ),
                "ready": True,
            },
        )
    )

    bridge = (
        RuntimeMonitoringBridge(
            manager
        )
    )

    result = bridge.health()

    eq(
        result[
            "status"
        ],
        "healthy",
        "monitoring bridge status",
    )

    eq(
        result[
            "runtime"
        ][
            "probe_count"
        ],
        1,
        "monitoring bridge includes detailed runtime probe payload",
    )


def test_check_one_and_status():
    manager = (
        RuntimeHealthManager()
    )

    manager.register(
        RuntimeProbe(
            "single",
            lambda: {
                "status": (
                    "healthy"
                ),
                "ready": True,
                "details": {
                    "x": 1,
                },
            },
        )
    )

    one = manager.check_one(
        "single"
    )

    eq(
        one[
            "details"
        ][
            "x"
        ],
        1,
        "check_one returns probe details",
    )

    eq(
        manager.status()[
            "total_checks"
        ],
        1,
        "health manager tracks checks",
    )

    expect_error(
        KeyError,
        lambda: manager.check_one(
            "missing"
        ),
        "unknown health probe rejected",
    )


def test_duplicate_probe():
    manager = (
        RuntimeHealthManager()
    )

    probe = RuntimeProbe(
        "same",
        lambda: {
            "status": (
                "healthy"
            ),
            "ready": True,
        },
    )

    manager.register(
        probe
    )

    expect_error(
        ValueError,
        lambda: manager.register(
            probe
        ),
        "duplicate probe rejected",
    )


def main():
    try:
        test_probe_result()
        test_probe_exception()
        test_manager_aggregation()
        test_required_failure()
        test_real_runtime_adapters()
        test_service_host_adapter()
        test_process_supervisor_adapter()
        test_monitoring_bridge()
        test_check_one_and_status()
        test_duplicate_probe()

    finally:
        cleanup()

    print(
        "RUNTIME HEALTH TEST SUITE: PASS"
    )
    print(
        "Assertions passed:",
        ASSERTIONS,
    )
    print(
        "Files validated: 4/4"
    )
    print(
        "Required/optional probe aggregation: VALIDATED"
    )
    print(
        "Lifecycle health adapter: VALIDATED"
    )
    print(
        "WorkerPool health adapter: VALIDATED"
    )
    print(
        "RuntimeStorage health adapter: VALIDATED"
    )
    print(
        "ServiceHost health adapter: VALIDATED"
    )
    print(
        "ProcessSupervisor health adapter: VALIDATED"
    )
    print(
        "Monitoring bridge payload: VALIDATED"
    )
    print(
        "Third-party dependencies: 0"
    )


main()
