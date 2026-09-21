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
    "gateway.py",
    "server.py",
    "factory.py",
]:
    path = SERVER_BASE + filename

    source = open(
        path,
        "r",
        encoding="utf-8",
    ).read()

    if "import " in source:
        raise AssertionError(
            "runtime server implementation contains forbidden import: "
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
    "runtime/server/"
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


def build_server(
    auth_required=False,
    context_enricher=None,
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

    routes = [
        GatewayRoute(
            "POST",
            "/v1/echo",
            "echo_service",
            "echo",
            auth_required=(
                auth_required
            ),
            max_payload_bytes=2048,
        ),
        GatewayRoute(
            "POST",
            "/admin/status",
            "runtime_control",
            "status",
            auth_required=False,
            max_payload_bytes=1024,
        ),
    ]

    server_config = (
        RuntimeServerConfig(
            host="127.0.0.1",
            port=0,
            routes=routes,
            context_enricher=(
                context_enricher
            ),
            timeout_seconds=3.0,
        )
    )

    server = (
        RuntimeServerFactory()
        .create(
            system_spec,
            server_config,
        )
    )

    return server


def serve_one(
    server,
    errors,
):
    try:
        server.serve_once()

    except BaseException as error:
        errors.append(
            error
        )


def test_config():
    route = GatewayRoute(
        "POST",
        "/x",
        "service",
        "run",
    )

    config = RuntimeServerConfig(
        routes=[
            route,
        ],
    )

    eq(
        config.public_dict()[
            "routes"
        ][
            0
        ][
            "path"
        ],
        "/x",
        "server config exposes route",
    )

    eq(
        config.port,
        0,
        "server config supports ephemeral port",
    )


def test_factory_not_started():
    server = build_server()

    eq(
        server.running,
        False,
        "server factory does not auto-start",
    )

    eq(
        server.system.status()[
            "running"
        ],
        False,
        "composed runtime remains stopped before server start",
    )


def test_start_and_real_http():
    server = build_server()

    server.start()

    check(
        server.http_server.port > 0,
        "HTTP server resolves ephemeral port",
    )

    errors = []

    thread = threading.Thread(
        target=serve_one,
        args=(
            server,
            errors,
        ),
    )

    thread.start()

    client = RawHTTPClient(
        "127.0.0.1",
        server.http_server.port,
        timeout_seconds=3.0,
    )

    codec = RuntimeJSONCodec()

    response = client.request(
        "POST",
        "/v1/echo",
        body=codec.encode({
            "hello": "world",
        }),
        headers={
            "content-type": (
                "application/json"
            ),
            "x-trace-id": (
                "trace-server"
            ),
        },
    )

    thread.join(
        timeout=4.0
    )

    eq(
        errors,
        [],
        "real HTTP serve_once completes without errors",
    )

    eq(
        response[
            "status"
        ],
        200,
        "real HTTP request returns 200",
    )

    public = codec.decode(
        response[
            "body"
        ]
    )

    eq(
        public[
            "data"
        ][
            "echo"
        ][
            "hello"
        ],
        "world",
        "HTTP request reaches composed hosted service",
    )

    eq(
        public[
            "trace_id"
        ],
        "trace-server",
        "HTTP trace id propagates through gateway/runtime",
    )

    eq(
        server.system
        .components
        .get(
            "observability"
        )
        .status()[
            "total_success"
        ],
        1,
        "HTTP request recorded by runtime observability",
    )

    server.stop()


def test_http_control_plane():
    server = build_server()

    server.start()

    errors = []

    thread = threading.Thread(
        target=serve_one,
        args=(
            server,
            errors,
        ),
    )

    thread.start()

    client = RawHTTPClient(
        "127.0.0.1",
        server.http_server.port,
        timeout_seconds=3.0,
    )

    codec = RuntimeJSONCodec()

    response = client.request(
        "POST",
        "/admin/status",
        body=codec.encode({}),
        headers={
            "content-type": (
                "application/json"
            ),
        },
    )

    thread.join(
        timeout=4.0
    )

    public = codec.decode(
        response[
            "body"
        ]
    )

    eq(
        response[
            "status"
        ],
        200,
        "HTTP control-plane status returns 200",
    )

    eq(
        public[
            "data"
        ][
            "operation"
        ],
        "status",
        "HTTP gateway reaches runtime control service",
    )

    server.stop()


def test_auth_boundary():
    denied_server = build_server(
        auth_required=True
    )

    denied_server.start()

    denied_errors = []

    denied_thread = threading.Thread(
        target=serve_one,
        args=(
            denied_server,
            denied_errors,
        ),
    )

    denied_thread.start()

    client = RawHTTPClient(
        "127.0.0.1",
        denied_server.http_server.port,
        timeout_seconds=3.0,
    )

    codec = RuntimeJSONCodec()

    denied = client.request(
        "POST",
        "/v1/echo",
        body=codec.encode({
            "x": 1,
        }),
        headers={
            "content-type": (
                "application/json"
            ),
            "authorization": (
                "Bearer ignored-by-transport"
            ),
        },
    )

    denied_thread.join(
        timeout=4.0
    )

    eq(
        denied[
            "status"
        ],
        401,
        "raw authorization header is not trusted automatically",
    )

    denied_server.stop()

    allowed_server = build_server(
        auth_required=True,
        context_enricher=(
            lambda request: {
                "authenticated": True,
            }
        ),
    )

    allowed_server.start()

    allowed_errors = []

    allowed_thread = threading.Thread(
        target=serve_one,
        args=(
            allowed_server,
            allowed_errors,
        ),
    )

    allowed_thread.start()

    allowed_client = RawHTTPClient(
        "127.0.0.1",
        allowed_server.http_server.port,
        timeout_seconds=3.0,
    )

    allowed = allowed_client.request(
        "POST",
        "/v1/echo",
        body=codec.encode({
            "x": 2,
        }),
        headers={
            "content-type": (
                "application/json"
            ),
        },
    )

    allowed_thread.join(
        timeout=4.0
    )

    eq(
        allowed[
            "status"
        ],
        200,
        "trusted context enricher can authenticate route",
    )

    allowed_server.stop()


def test_route_not_found():
    server = build_server()
    server.start()

    errors = []

    thread = threading.Thread(
        target=serve_one,
        args=(
            server,
            errors,
        ),
    )

    thread.start()

    client = RawHTTPClient(
        "127.0.0.1",
        server.http_server.port,
        timeout_seconds=3.0,
    )

    response = client.request(
        "GET",
        "/missing",
    )

    thread.join(
        timeout=4.0
    )

    eq(
        response[
            "status"
        ],
        404,
        "missing HTTP route returns 404",
    )

    server.stop()


def test_finite_serve():
    server = build_server()
    server.start()

    errors = []

    thread = threading.Thread(
        target=lambda: (
            server.serve(
                2
            )
        ),
    )

    thread.start()

    client = RawHTTPClient(
        "127.0.0.1",
        server.http_server.port,
        timeout_seconds=3.0,
    )

    codec = RuntimeJSONCodec()

    first = client.request(
        "POST",
        "/v1/echo",
        body=codec.encode({
            "n": 1,
        }),
        headers={
            "content-type": (
                "application/json"
            ),
        },
    )

    second = client.request(
        "POST",
        "/v1/echo",
        body=codec.encode({
            "n": 2,
        }),
        headers={
            "content-type": (
                "application/json"
            ),
        },
    )

    thread.join(
        timeout=5.0
    )

    eq(
        first[
            "status"
        ],
        200,
        "first finite serve request succeeds",
    )

    eq(
        second[
            "status"
        ],
        200,
        "second finite serve request succeeds",
    )

    eq(
        server.serve_count,
        2,
        "finite serve count tracked",
    )

    server.stop()


def test_stop_runtime():
    server = build_server()

    server.start()
    server.stop()

    eq(
        server.running,
        False,
        "application server stops",
    )

    eq(
        server.system.status()[
            "application"
        ][
            "stopped"
        ],
        True,
        "application server stop tears down composed runtime",
    )

    eq(
        server.http_server
        .status()[
            "running"
        ],
        False,
        "application server stop closes HTTP listener",
    )


def main():
    try:
        test_config()
        test_factory_not_started()
        test_start_and_real_http()
        test_http_control_plane()
        test_auth_boundary()
        test_route_not_found()
        test_finite_serve()
        test_stop_runtime()

    finally:
        cleanup()

    print(
        "RUNTIME SERVER TEST SUITE: PASS"
    )
    print(
        "Assertions passed:",
        ASSERTIONS,
    )
    print(
        "Files validated: 4/4"
    )
    print(
        "RuntimeSystem -> APIGateway -> HTTP composition: VALIDATED"
    )
    print(
        "Real socket HTTP request path: VALIDATED"
    )
    print(
        "Runtime control service over HTTP: VALIDATED"
    )
    print(
        "Trusted authentication boundary: VALIDATED"
    )
    print(
        "Transactional server startup/shutdown: VALIDATED"
    )
    print(
        "Finite controllable serve loop: VALIDATED"
    )
    print(
        "Third-party dependencies: 0"
    )
    print(
        "Transport dependency inherited from runtime/http: socket"
    )
    print(
        "Test-only concurrency dependency: threading"
    )


main()
