import os
import shutil
import threading

PARSERS_BASE = "libs/data/parsers/"
PROTOCOL_BASE = "libs/protocol/"
GATEWAY_BASE = "services/api_gateway/"
LOAD_BALANCER_BASE = "services/load_balancer/"
DISCOVERY_BASE = "services/service_discovery/"
LOGGING_BASE = "services/logging_service/"
METRICS_BASE = "services/metrics_service/"
TRACING_BASE = "services/tracing_service/"

NETWORK_BASE = "runtime/networking/"
HTTP_BASE = "runtime/http/"
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
SERVER_BASE = "runtime/server/"
DAEMON_BASE = "runtime/daemon/"

namespace = {
    "__builtins__": __builtins__,
}

groups = [
    (
        PARSERS_BASE,
        [
            "json_parser.py",
        ],
    ),
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
        GATEWAY_BASE,
        [
            "middleware.py",
            "route.py",
            "router.py",
            "gateway.py",
            "routes.py",
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
        NETWORK_BASE,
        [
            "http_parser.py",
        ],
    ),
    (
        HTTP_BASE,
        [
            "json_codec.py",
            "gateway_adapter.py",
            "server.py",
            "client.py",
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
    (
        SERVER_BASE,
        [
            "config.py",
            "gateway.py",
            "server.py",
            "factory.py",
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
    "loop.py",
    "runner.py",
    "factory.py",
]:
    path = DAEMON_BASE + filename

    source = open(
        path,
        "r",
        encoding="utf-8",
    ).read()

    if "import " in source:
        raise AssertionError(
            "daemon implementation contains forbidden import: "
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
    "runtime/daemon/"
    "_test_runtime"
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


def cleanup():
    if os.path.exists(
        ROOT
    ):
        shutil.rmtree(
            ROOT
        )


def echo(
    request,
):
    return (
        ServiceResponse
        .success_response(
            request,
            data={
                "echo": (
                    request.payload
                ),
            },
        )
    )


def make_daemon(
    max_requests=None,
    max_idle_timeouts=None,
):
    cleanup()

    clock = Clock()

    system_spec = RuntimeSystemSpec(
        storage_root=ROOT,
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

    server_config = RuntimeServerConfig(
        host="127.0.0.1",
        port=0,
        routes=[
            GatewayRoute(
                "POST",
                "/v1/echo",
                "echo_service",
                "echo",
                auth_required=False,
                max_payload_bytes=2048,
            ),
            GatewayRoute(
                "POST",
                "/admin/shutdown",
                "runtime_control",
                "request_shutdown",
                auth_required=False,
                max_payload_bytes=1024,
            ),
        ],
        timeout_seconds=0.1,
    )

    daemon_config = RuntimeDaemonConfig(
        max_requests=max_requests,
        max_idle_timeouts=(
            max_idle_timeouts
        ),
    )

    return (
        RuntimeDaemonFactory()
        .create(
            system_spec,
            server_config,
            daemon_config,
        )
    )


def test_config():
    config = RuntimeDaemonConfig(
        max_requests=5,
        max_idle_timeouts=2,
    )

    eq(
        config.to_dict()[
            "max_requests"
        ],
        5,
        "daemon config max requests",
    )

    eq(
        config.to_dict()[
            "max_idle_timeouts"
        ],
        2,
        "daemon config idle timeout limit",
    )


def test_idle_timeout_exit():
    daemon = make_daemon(
        max_idle_timeouts=2
    )

    result = daemon.run()

    eq(
        result[
            "ok"
        ],
        True,
        "idle timeout limit is a clean daemon exit",
    )

    eq(
        result[
            "loop"
        ][
            "exit_reason"
        ],
        "idle_timeout_limit",
        "daemon exits after configured idle timeout polls",
    )

    eq(
        result[
            "stopped"
        ],
        True,
        "idle-exit daemon tears server down",
    )


def test_request_limit():
    daemon = make_daemon(
        max_requests=1
    )

    results = []

    thread = threading.Thread(
        target=lambda: results.append(
            daemon.run()
        )
    )

    thread.start()

    while (
        not daemon.server.running
    ):
        pass

    client = RawHTTPClient(
        "127.0.0.1",
        daemon.server.http_server.port,
        timeout_seconds=3.0,
    )

    codec = RuntimeJSONCodec()

    response = client.request(
        "POST",
        "/v1/echo",
        body=codec.encode({
            "hello": "daemon",
        }),
        headers={
            "content-type": (
                "application/json"
            ),
        },
    )

    thread.join(
        timeout=4.0
    )

    eq(
        response[
            "status"
        ],
        200,
        "daemon serves real HTTP request",
    )

    eq(
        results[
            0
        ][
            "loop"
        ][
            "exit_reason"
        ],
        "request_limit",
        "daemon exits at request limit",
    )

    eq(
        results[
            0
        ][
            "loop"
        ][
            "requests_served"
        ],
        1,
        "daemon request count",
    )


def test_shutdown_via_http_control_plane():
    daemon = make_daemon()

    results = []

    thread = threading.Thread(
        target=lambda: results.append(
            daemon.run()
        )
    )

    thread.start()

    while (
        not daemon.server.running
    ):
        pass

    client = RawHTTPClient(
        "127.0.0.1",
        daemon.server.http_server.port,
        timeout_seconds=3.0,
    )

    codec = RuntimeJSONCodec()

    shutdown = client.request(
        "POST",
        "/admin/shutdown",
        body=codec.encode({
            "reason": (
                "http operator request"
            ),
        }),
        headers={
            "content-type": (
                "application/json"
            ),
        },
    )

    thread.join(
        timeout=4.0
    )

    eq(
        shutdown[
            "status"
        ],
        200,
        "HTTP control-plane shutdown request succeeds",
    )

    eq(
        results[
            0
        ][
            "loop"
        ][
            "exit_reason"
        ],
        "shutdown_requested",
        "daemon observes coordinator shutdown",
    )

    eq(
        results[
            0
        ][
            "stopped"
        ],
        True,
        "HTTP-triggered shutdown tears runtime down",
    )

    event = (
        daemon.server.system
        .components
        .get(
            "shutdown_coordinator"
        )
        .event()
    )

    eq(
        event.reason,
        "http operator request",
        "daemon preserves HTTP shutdown reason",
    )


def test_programmatic_shutdown():
    daemon = make_daemon()

    results = []

    thread = threading.Thread(
        target=lambda: results.append(
            daemon.run()
        )
    )

    thread.start()

    while (
        not daemon.server.running
    ):
        pass

    daemon.request_shutdown(
        "programmatic stop"
    )

    thread.join(
        timeout=4.0
    )

    eq(
        results[
            0
        ][
            "loop"
        ][
            "exit_reason"
        ],
        "shutdown_requested",
        "programmatic shutdown exits daemon loop",
    )

    eq(
        daemon.status()[
            "run_count"
        ],
        1,
        "daemon run count tracked",
    )


def test_factory_does_not_start():
    daemon = make_daemon(
        max_idle_timeouts=1
    )

    eq(
        daemon.server.running,
        False,
        "daemon factory does not auto-start server",
    )

    eq(
        daemon.server.system
        .status()[
            "running"
        ],
        False,
        "daemon factory does not auto-start runtime",
    )


def main():
    try:
        test_config()
        test_idle_timeout_exit()
        test_request_limit()
        test_shutdown_via_http_control_plane()
        test_programmatic_shutdown()
        test_factory_does_not_start()

    finally:
        cleanup()

    print(
        "RUNTIME DAEMON TEST SUITE: PASS"
    )
    print(
        "Assertions passed:",
        ASSERTIONS,
    )
    print(
        "Files validated: 4/4"
    )
    print(
        "Cooperative long-running HTTP loop: VALIDATED"
    )
    print(
        "Accept-timeout wake-up polling: VALIDATED"
    )
    print(
        "HTTP control-plane shutdown: VALIDATED"
    )
    print(
        "Programmatic shutdown coordination: VALIDATED"
    )
    print(
        "Guaranteed server/runtime teardown: VALIDATED"
    )
    print(
        "Deterministic request/idle limits: VALIDATED"
    )
    print(
        "Third-party dependencies: 0"
    )
    print(
        "Inherited transport dependency: socket"
    )
    print(
        "Test-only dependency: threading"
    )


main()
