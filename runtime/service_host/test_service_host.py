PROTOCOL_BASE = "libs/protocol/"
LOAD_BALANCER_BASE = "services/load_balancer/"
DISCOVERY_BASE = "services/service_discovery/"
GATEWAY_BASE = "services/api_gateway/"
LIFECYCLE_BASE = "runtime/lifecycle/"
HOST_BASE = "runtime/service_host/"

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
        LIFECYCLE_BASE,
        [
            "resource.py",
            "graph.py",
            "manager.py",
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
    "binding.py",
    "registry.py",
    "host.py",
    "gateway_dispatcher.py",
    "lifecycle_adapter.py",
]:
    path = HOST_BASE + filename

    source = open(
        path,
        "r",
        encoding="utf-8",
    ).read()

    if "import " in source:
        raise AssertionError(
            "service-host implementation contains forbidden import: "
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
    def __init__(
        self,
        name,
    ):
        self.name = name

    def handle(
        self,
        request,
    ):
        return (
            ServiceResponse
            .success_response(
                request,
                data={
                    "instance": (
                        self.name
                    ),
                    "payload": (
                        request.payload
                    ),
                },
            )
        )


def test_binding_object_handler():
    service = EchoService(
        "one"
    )

    binding = ServiceBinding(
        "echo-1",
        "echo_service",
        service,
        metadata={
            "zone": "a",
        },
    )

    eq(
        binding.instance_id,
        "echo-1",
        "binding instance id",
    )

    eq(
        binding.endpoint,
        (
            "local://echo_service/"
            "echo-1"
        ),
        "default local endpoint",
    )

    request = ServiceRequest(
        "r1",
        "echo_service",
        "echo",
    )

    eq(
        binding.handler(
            request
        ).data[
            "instance"
        ],
        "one",
        "object.handle resolved as binding handler",
    )


def test_registry_order():
    registry = HostBindingRegistry()

    registry.add(
        ServiceBinding(
            "a",
            "echo_service",
            EchoService(
                "a"
            ),
        )
    )

    registry.add(
        ServiceBinding(
            "b",
            "echo_service",
            EchoService(
                "b"
            ),
        )
    )

    eq(
        [
            item.instance_id
            for item
            in registry.bindings()
        ],
        [
            "a",
            "b",
        ],
        "host registry preserves binding order",
    )

    eq(
        [
            item.instance_id
            for item
            in registry.instances(
                "echo_service"
            )
        ],
        [
            "a",
            "b",
        ],
        "host registry groups service instances",
    )


def test_dispatch_two_instances():
    host = ServiceHost()

    host.add_service(
        "echo-1",
        "echo_service",
        EchoService(
            "one"
        ),
    )

    host.add_service(
        "echo-2",
        "echo_service",
        EchoService(
            "two"
        ),
    )

    host.start(
        100
    )

    first = host.dispatch(
        ServiceRequest(
            "r1",
            "echo_service",
            "echo",
            payload={
                "x": 1,
            },
        )
    )

    second = host.dispatch(
        ServiceRequest(
            "r2",
            "echo_service",
            "echo",
            payload={
                "x": 2,
            },
        )
    )

    eq(
        first.success,
        True,
        "first host dispatch succeeds",
    )

    eq(
        second.success,
        True,
        "second host dispatch succeeds",
    )

    eq(
        {
            first.data[
                "instance"
            ],
            second.data[
                "instance"
            ],
        },
        {
            "one",
            "two",
        },
        "round-robin host uses both local instances",
    )

    eq(
        host.status(
            101
        )[
            "discovery"
        ][
            "local_bound_instance_count"
        ],
        2,
        "all hosted instances bound through discovery",
    )

    host.stop()


def test_not_running_response():
    host = ServiceHost()

    host.add_service(
        "echo-1",
        "echo_service",
        EchoService(
            "one"
        ),
    )

    response = host.dispatch(
        ServiceRequest(
            "r",
            "echo_service",
            "echo",
        )
    )

    eq(
        response.success,
        False,
        "stopped host returns protocol error",
    )

    eq(
        response.error.code,
        "SERVICE_HOST_NOT_RUNNING",
        "stopped host error code",
    )


def test_stale_instance():
    host = ServiceHost()

    host.add_service(
        "echo-1",
        "echo_service",
        EchoService(
            "one"
        ),
        lease_seconds=5,
    )

    host.start(
        10
    )

    stale = host.sweep_stale(
        15
    )

    eq(
        stale[
            "stale_instance_ids"
        ],
        [
            "echo-1",
        ],
        "host stale sweep finds expired lease",
    )

    response = host.dispatch(
        ServiceRequest(
            "r",
            "echo_service",
            "echo",
        )
    )

    eq(
        response.success,
        False,
        "stale local instance no longer serves requests",
    )

    host.heartbeat(
        "echo-1",
        15,
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
        "heartbeat recovers hosted instance",
    )

    host.stop()


def test_manual_health():
    host = ServiceHost()

    host.add_service(
        "echo-1",
        "echo_service",
        EchoService(
            "one"
        ),
    )

    host.start(
        1
    )

    host.mark_unhealthy(
        "echo-1"
    )

    eq(
        host.dispatch(
            ServiceRequest(
                "r1",
                "echo_service",
                "echo",
            )
        ).success,
        False,
        "manual unhealthy state removes traffic",
    )

    host.mark_healthy(
        "echo-1"
    )

    eq(
        host.dispatch(
            ServiceRequest(
                "r2",
                "echo_service",
                "echo",
            )
        ).success,
        True,
        "manual health recovery restores traffic",
    )

    host.disable(
        "echo-1"
    )

    eq(
        host.dispatch(
            ServiceRequest(
                "r3",
                "echo_service",
                "echo",
            )
        ).success,
        False,
        "disabled service instance does not serve traffic",
    )

    host.enable(
        "echo-1"
    )

    eq(
        host.dispatch(
            ServiceRequest(
                "r4",
                "echo_service",
                "echo",
            )
        ).success,
        True,
        "enabled service instance serves traffic again",
    )

    host.stop()


def test_gateway_integration():
    host = ServiceHost()

    host.add_service(
        "echo-1",
        "echo_service",
        EchoService(
            "hosted"
        ),
    )

    host.start(
        100
    )

    router = GatewayRouter()

    router.add(
        GatewayRoute(
            "POST",
            "/v1/echo",
            "echo_service",
            "echo",
            auth_required=False,
        )
    )

    gateway = APIGateway(
        router=router,
        dispatcher=(
            HostGatewayDispatcher(
                host
            )
        ),
    )

    public = gateway.handle(
        GatewayContext(
            method="POST",
            path="/v1/echo",
            payload={
                "hello": "world",
            },
        )
    )

    eq(
        public[
            "status"
        ],
        200,
        "API gateway dispatches through service host",
    )

    eq(
        public[
            "data"
        ][
            "instance"
        ],
        "hosted",
        "gateway response produced by hosted service",
    )

    eq(
        public[
            "data"
        ][
            "payload"
        ][
            "hello"
        ],
        "world",
        "gateway payload reaches hosted service",
    )

    host.stop()


def test_load_balancer_retry():
    calls = {
        "bad": 0,
        "good": 0,
    }

    def bad(
        request,
    ):
        calls[
            "bad"
        ] += 1

        raise RuntimeError(
            "instance failed"
        )

    def good(
        request,
    ):
        calls[
            "good"
        ] += 1

        return (
            ServiceResponse
            .success_response(
                request,
                data={
                    "instance": "good",
                },
            )
        )

    host = ServiceHost(
        load_balancer=LoadBalancer(
            max_attempts=2
        )
    )

    host.add_service(
        "first",
        "service",
        bad,
        max_consecutive_failures=1,
    )

    host.add_service(
        "second",
        "service",
        good,
    )

    host.start(
        1
    )

    response = host.dispatch(
        ServiceRequest(
            "retry",
            "service",
            "run",
        )
    )

    eq(
        response.success,
        True,
        "load balancer retries another hosted instance",
    )

    eq(
        response.data[
            "instance"
        ],
        "good",
        "retry reaches healthy second instance",
    )

    eq(
        calls,
        {
            "bad": 1,
            "good": 1,
        },
        "failed and successful handlers called once",
    )

    eq(
        host.load_balancer
        .registry
        .get(
            "first"
        ).healthy,
        False,
        "failed hosted instance marked unhealthy at configured threshold",
    )

    host.stop()


def test_transactional_start_rollback():
    balancer = LoadBalancer()

    discovery = ServiceDiscoveryManager(
        load_balancer=balancer
    )

    discovery.register_local(
        "duplicate",
        "external_service",
        EchoService(
            "external"
        ).handle,
        now=1,
    )

    host = ServiceHost(
        load_balancer=balancer,
        discovery=discovery,
    )

    host.add_service(
        "first",
        "echo_service",
        EchoService(
            "first"
        ),
    )

    host.add_service(
        "duplicate",
        "echo_service",
        EchoService(
            "duplicate"
        ),
    )

    expect_error(
        ValueError,
        lambda: host.start(
            2
        ),
        "host start failure propagated",
    )

    eq(
        balancer.registry.count(
            "echo_service"
        ),
        0,
        "partial host registrations rolled back",
    )

    eq(
        balancer.registry.count(
            "external_service"
        ),
        1,
        "pre-existing discovery binding preserved",
    )

    eq(
        host.running,
        False,
        "failed host start does not enter running state",
    )


def test_stop_reverse_order():
    host = ServiceHost()

    host.add_service(
        "one",
        "svc",
        EchoService(
            "one"
        ),
    )

    host.add_service(
        "two",
        "svc",
        EchoService(
            "two"
        ),
    )

    host.start(
        1
    )

    result = host.stop()

    eq(
        result[
            "deregistered"
        ],
        [
            "two",
            "one",
        ],
        "host deregisters in reverse binding order",
    )

    eq(
        host.load_balancer
        .registry
        .count(
            "svc"
        ),
        0,
        "stop clears hosted instances from load balancer",
    )


def test_lifecycle_adapter():
    host = ServiceHost()

    host.add_service(
        "echo-1",
        "echo_service",
        EchoService(
            "life"
        ),
    )

    lifecycle = (
        LifecycleManager()
    )

    lifecycle.register(
        ServiceHostLifecycleAdapter
        .resource(
            name="services",
            host=host,
            now_provider=(
                lambda: 50
            ),
        )
    )

    lifecycle.start_all()

    eq(
        host.running,
        True,
        "lifecycle adapter starts service host",
    )

    eq(
        host.started_at,
        50,
        "lifecycle adapter supplies start time",
    )

    lifecycle.stop_all()

    eq(
        host.running,
        False,
        "lifecycle adapter stops service host",
    )


def test_add_while_running_rejected():
    host = ServiceHost()

    host.start(
        1
    )

    expect_error(
        RuntimeError,
        lambda: host.add_service(
            "late",
            "service",
            EchoService(
                "late"
            ),
        ),
        "running host rejects topology mutation",
    )

    host.stop()


def main():
    test_binding_object_handler()
    test_registry_order()
    test_dispatch_two_instances()
    test_not_running_response()
    test_stale_instance()
    test_manual_health()
    test_gateway_integration()
    test_load_balancer_retry()
    test_transactional_start_rollback()
    test_stop_reverse_order()
    test_lifecycle_adapter()
    test_add_while_running_rejected()

    print(
        "RUNTIME SERVICE HOST TEST SUITE: PASS"
    )
    print(
        "Assertions passed:",
        ASSERTIONS,
    )
    print(
        "Files validated: 5/5"
    )
    print(
        "Service-object/callable bindings: VALIDATED"
    )
    print(
        "ServiceDiscovery + LoadBalancer hosting: VALIDATED"
    )
    print(
        "Multi-instance routing/retry: VALIDATED"
    )
    print(
        "Lease heartbeat/stale health propagation: VALIDATED"
    )
    print(
        "APIGateway dispatcher integration: VALIDATED"
    )
    print(
        "Transactional startup rollback: VALIDATED"
    )
    print(
        "Lifecycle adapter integration: VALIDATED"
    )
    print(
        "Third-party dependencies: 0"
    )


main()
