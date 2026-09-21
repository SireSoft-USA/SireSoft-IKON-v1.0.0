SERIAL_BASE = "libs/core/serialization/"
PROTOCOL_BASE = "libs/protocol/"
LB_BASE = "services/load_balancer/"
SERVICE_BASE = "services/service_discovery/"

namespace = {
    "__builtins__": __builtins__,
}

groups = [
    (
        SERIAL_BASE,
        [
            "binary_writer.py",
            "binary_reader.py",
            "checksum.py",
        ],
    ),
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
        LB_BASE,
        [
            "instance.py",
            "registry.py",
            "strategies.py",
            "load_balancer.py",
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
    "descriptor.py",
    "registry.py",
    "manager.py",
    "service.py",
]:
    path = SERVICE_BASE + filename

    source = open(
        path,
        "r",
        encoding="utf-8",
    ).read()

    if "import " in source:
        raise AssertionError(
            "service_discovery implementation contains forbidden import: "
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


def successful_handler(
    request,
):
    return (
        ServiceResponse
        .success_response(
            request,
            data={
                "handled_by": (
                    request.service
                ),
            },
        )
    )


def test_descriptor_lease():
    descriptor = (
        ServiceDescriptor(
            instance_id="rag-1",
            service_name="rag_service",
            endpoint="local://rag/1",
            registered_at=100,
            lease_seconds=10,
        )
    )

    eq(
        descriptor.available(
            109
        ),
        True,
        "descriptor available before lease boundary",
    )

    eq(
        descriptor.stale(
            110
        ),
        True,
        "descriptor stale exactly at lease boundary",
    )

    descriptor.heartbeat(
        109
    )

    eq(
        descriptor.available(
            118
        ),
        True,
        "heartbeat extends lease",
    )


def test_registry_order():
    registry = DiscoveryRegistry()

    registry.register(
        ServiceDescriptor(
            "a",
            "rag_service",
            "tcp://a",
            1,
        )
    )

    registry.register(
        ServiceDescriptor(
            "b",
            "rag_service",
            "tcp://b",
            1,
        )
    )

    registry.register(
        ServiceDescriptor(
            "c",
            "retrieval_service",
            "tcp://c",
            1,
        )
    )

    eq(
        [
            item.instance_id
            for item
            in registry.instances(
                "rag_service"
            )
        ],
        [
            "a",
            "b",
        ],
        "discovery registry preserves instance order",
    )

    eq(
        registry.services(),
        [
            "rag_service",
            "retrieval_service",
        ],
        "discovery registry preserves service order",
    )


def test_registration_resolution():
    manager = (
        ServiceDiscoveryManager()
    )

    manager.register_instance(
        "rag-1",
        "rag_service",
        "rpc://rag-1",
        now=100,
        lease_seconds=60,
        metadata={
            "zone": "a",
        },
    )

    manager.register_instance(
        "rag-2",
        "rag_service",
        "rpc://rag-2",
        now=100,
        lease_seconds=60,
        metadata={
            "zone": "b",
        },
    )

    resolved = manager.resolve(
        "rag_service",
        now=120,
    )

    eq(
        resolved[
            "count"
        ],
        2,
        "both healthy instances resolved",
    )

    eq(
        resolved[
            "instances"
        ][0][
            "endpoint"
        ],
        "rpc://rag-1",
        "resolution returns endpoint",
    )

    eq(
        resolved[
            "instances"
        ][1][
            "metadata"
        ][
            "zone"
        ],
        "b",
        "resolution preserves metadata",
    )


def test_health_enable_filters():
    manager = (
        ServiceDiscoveryManager()
    )

    manager.register_instance(
        "x",
        "service",
        "rpc://x",
        now=1,
    )

    manager.mark_unhealthy(
        "x"
    )

    eq(
        manager.resolve(
            "service",
            now=2,
        )[
            "count"
        ],
        0,
        "unhealthy instance hidden from available resolution",
    )

    eq(
        manager.resolve(
            "service",
            now=2,
            available_only=False,
        )[
            "count"
        ],
        1,
        "unhealthy instance visible in full resolution",
    )

    manager.mark_healthy(
        "x"
    )

    manager.disable(
        "x"
    )

    eq(
        manager.resolve(
            "service",
            now=2,
        )[
            "count"
        ],
        0,
        "disabled instance not available",
    )

    manager.enable(
        "x"
    )

    eq(
        manager.resolve(
            "service",
            now=2,
        )[
            "count"
        ],
        1,
        "re-enabled healthy instance available",
    )


def test_stale_sweep():
    manager = (
        ServiceDiscoveryManager()
    )

    manager.register_instance(
        "a",
        "service",
        "rpc://a",
        now=100,
        lease_seconds=10,
    )

    manager.register_instance(
        "b",
        "service",
        "rpc://b",
        now=100,
        lease_seconds=30,
    )

    swept = manager.sweep_stale(
        110
    )

    eq(
        swept[
            "stale_instance_ids"
        ],
        [
            "a",
        ],
        "only expired lease marked stale",
    )

    eq(
        manager.registry.get(
            "a"
        ).healthy,
        False,
        "stale descriptor marked unhealthy",
    )

    eq(
        manager.registry.get(
            "b"
        ).healthy,
        True,
        "live descriptor remains healthy",
    )


def test_heartbeat_recovers():
    manager = (
        ServiceDiscoveryManager()
    )

    manager.register_instance(
        "a",
        "service",
        "rpc://a",
        now=1,
        lease_seconds=5,
    )

    manager.sweep_stale(
        6
    )

    eq(
        manager.registry.get(
            "a"
        ).healthy,
        False,
        "stale instance unhealthy before heartbeat",
    )

    manager.heartbeat(
        "a",
        6,
    )

    eq(
        manager.registry.get(
            "a"
        ).healthy,
        True,
        "heartbeat recovers descriptor health",
    )

    eq(
        manager.resolve(
            "service",
            now=7,
        )[
            "count"
        ],
        1,
        "heartbeat makes instance discoverable again",
    )


def test_local_load_balancer_binding():
    balancer = LoadBalancer()

    manager = (
        ServiceDiscoveryManager(
            load_balancer=balancer
        )
    )

    descriptor = manager.register_local(
        instance_id="rag-local-1",
        service_name="rag_service",
        handler=successful_handler,
        now=100,
        lease_seconds=20,
        metadata={
            "runtime": "local",
        },
    )

    eq(
        descriptor.local_bound,
        True,
        "local descriptor marked bound",
    )

    eq(
        balancer.registry.count(
            "rag_service"
        ),
        1,
        "discovery local registration enters load balancer",
    )

    request = ServiceRequest(
        "r1",
        "rag_service",
        "answer",
    )

    response = balancer.dispatch(
        request
    )

    eq(
        response.success,
        True,
        "load balancer dispatches discovered local instance",
    )

    eq(
        response.metadata[
            "load_balancer_instance_id"
        ],
        "rag-local-1",
        "load balancer reports discovered instance ID",
    )


def test_local_health_sync():
    balancer = LoadBalancer()

    manager = (
        ServiceDiscoveryManager(
            load_balancer=balancer
        )
    )

    manager.register_local(
        "local-1",
        "rag_service",
        successful_handler,
        now=1,
        lease_seconds=5,
    )

    manager.mark_unhealthy(
        "local-1"
    )

    eq(
        balancer.registry.get(
            "local-1"
        ).healthy,
        False,
        "discovery unhealthy state propagates to load balancer",
    )

    manager.mark_healthy(
        "local-1"
    )

    eq(
        balancer.registry.get(
            "local-1"
        ).healthy,
        True,
        "discovery healthy state propagates to load balancer",
    )

    manager.disable(
        "local-1"
    )

    eq(
        balancer.registry.get(
            "local-1"
        ).accepting_requests,
        False,
        "discovery disable pauses load balancer instance",
    )

    manager.enable(
        "local-1"
    )

    eq(
        balancer.registry.get(
            "local-1"
        ).accepting_requests,
        True,
        "discovery enable resumes load balancer instance",
    )


def test_stale_local_removes_from_lb_availability():
    balancer = LoadBalancer()

    manager = (
        ServiceDiscoveryManager(
            load_balancer=balancer
        )
    )

    manager.register_local(
        "local-1",
        "rag_service",
        successful_handler,
        now=10,
        lease_seconds=5,
    )

    manager.sweep_stale(
        15
    )

    eq(
        balancer.registry.get(
            "local-1"
        ).healthy,
        False,
        "stale local discovery instance disables LB health",
    )

    response = balancer.dispatch(
        ServiceRequest(
            "r2",
            "rag_service",
            "answer",
        )
    )

    eq(
        response.success,
        False,
        "stale local instance no longer serves traffic",
    )


def test_deregister_local():
    balancer = LoadBalancer()

    manager = (
        ServiceDiscoveryManager(
            load_balancer=balancer
        )
    )

    manager.register_local(
        "local-1",
        "rag_service",
        successful_handler,
        now=1,
    )

    removed = manager.deregister(
        "local-1"
    )

    eq(
        removed.instance_id,
        "local-1",
        "deregister returns descriptor",
    )

    eq(
        balancer.registry.count(
            "rag_service"
        ),
        0,
        "deregister removes local load balancer instance",
    )

    expect_error(
        KeyError,
        lambda: manager.registry.get(
            "local-1"
        ),
        "deregister removes discovery descriptor",
    )


def test_status():
    manager = (
        ServiceDiscoveryManager()
    )

    manager.register_instance(
        "a",
        "rag_service",
        "rpc://a",
        now=1,
    )

    manager.register_instance(
        "b",
        "retrieval_service",
        "rpc://b",
        now=1,
    )

    status = manager.status(
        now=2
    )

    eq(
        status[
            "service_count"
        ],
        2,
        "status service count",
    )

    eq(
        status[
            "instance_count"
        ],
        2,
        "status instance count",
    )

    eq(
        status[
            "available_instance_count"
        ],
        2,
        "status available instance count",
    )

    eq(
        status[
            "load_balancer_attached"
        ],
        False,
        "status reports LB attachment",
    )


def test_service_flow():
    manager = (
        ServiceDiscoveryManager()
    )

    service = ServiceDiscoveryService(
        manager
    )

    registered = service.handle(
        ServiceRequest(
            "s1",
            "service_discovery",
            "register",
            payload={
                "instance_id": "rag-1",
                "service_name": "rag_service",
                "endpoint": "rpc://rag-1",
                "now": 100,
                "lease_seconds": 20,
            },
        )
    )

    eq(
        registered.success,
        True,
        "discovery service registration succeeds",
    )

    resolved = service.handle(
        ServiceRequest(
            "s2",
            "service_discovery",
            "resolve",
            payload={
                "service_name": "rag_service",
                "now": 101,
            },
        )
    )

    eq(
        resolved.data[
            "resolution"
        ][
            "count"
        ],
        1,
        "discovery service resolves registered instance",
    )

    heartbeat = service.handle(
        ServiceRequest(
            "s3",
            "service_discovery",
            "heartbeat",
            payload={
                "instance_id": "rag-1",
                "now": 110,
            },
        )
    )

    eq(
        heartbeat.data[
            "instance"
        ][
            "last_heartbeat"
        ],
        110,
        "service heartbeat updates lease timestamp",
    )


def test_protocol_round_trip():
    service = (
        ServiceDiscoveryService(
            ServiceDiscoveryManager()
        )
    )

    codec = ProtocolCodec()

    request = ServiceRequest(
        "protocol-discovery",
        "service_discovery",
        "register",
        payload={
            "instance_id": (
                "retrieval-1"
            ),
            "service_name": (
                "retrieval_service"
            ),
            "endpoint": (
                "rpc://retrieval-1"
            ),
            "now": 10,
            "metadata": {
                "zone": "local",
            },
        },
        trace_id=(
            "trace-discovery"
        ),
    )

    request = (
        codec.decode_request(
            codec.encode_request(
                request
            )
        )
    )

    response = service.handle(
        request
    )

    response = (
        codec.decode_response(
            codec.encode_response(
                response
            )
        )
    )

    eq(
        response.success,
        True,
        "discovery registration survives binary protocol",
    )

    eq(
        response.trace_id,
        "trace-discovery",
        "discovery trace preserved",
    )

    eq(
        response.data[
            "instance"
        ][
            "metadata"
        ][
            "zone"
        ],
        "local",
        "discovery metadata survives protocol",
    )


def test_errors():
    service = (
        ServiceDiscoveryService(
            ServiceDiscoveryManager()
        )
    )

    missing = service.handle(
        ServiceRequest(
            "e1",
            "service_discovery",
            "get_instance",
            payload={
                "instance_id": "missing",
            },
        )
    )

    eq(
        missing.error.code,
        "NOT_FOUND",
        "missing instance maps to NOT_FOUND",
    )

    invalid = service.handle(
        ServiceRequest(
            "e2",
            "service_discovery",
            "register",
            payload={
                "instance_id": "x",
                "service_name": "x",
                "endpoint": "",
                "now": 1,
            },
        )
    )

    eq(
        invalid.error.code,
        "INVALID_REQUEST",
        "invalid registration maps to INVALID_REQUEST",
    )

    wrong = service.handle(
        ServiceRequest(
            "e3",
            "rag_service",
            "status",
        )
    )

    eq(
        wrong.error.code,
        "INVALID_REQUEST",
        "wrong target service rejected",
    )

    expect_error(
        TypeError,
        lambda: service.handle(
            {}
        ),
        "non-ServiceRequest rejected",
    )


def test_validation():
    manager = (
        ServiceDiscoveryManager()
    )

    manager.register_instance(
        "x",
        "service",
        "rpc://x",
        now=100,
    )

    expect_error(
        ValueError,
        lambda: manager.register_instance(
            "x",
            "service",
            "rpc://x2",
            now=100,
        ),
        "duplicate discovery instance rejected",
    )

    expect_error(
        ValueError,
        lambda: manager.heartbeat(
            "x",
            99,
        ),
        "backward heartbeat time rejected",
    )

    expect_error(
        RuntimeError,
        lambda: manager.bind_local_handler(
            "x",
            successful_handler,
        ),
        "local bind requires attached load balancer",
    )


def main():
    test_descriptor_lease()
    test_registry_order()
    test_registration_resolution()
    test_health_enable_filters()
    test_stale_sweep()
    test_heartbeat_recovers()
    test_local_load_balancer_binding()
    test_local_health_sync()
    test_stale_local_removes_from_lb_availability()
    test_deregister_local()
    test_status()
    test_service_flow()
    test_protocol_round_trip()
    test_errors()
    test_validation()

    print(
        "SERVICE DISCOVERY TEST SUITE: PASS"
    )
    print(
        "Assertions passed:",
        ASSERTIONS,
    )
    print(
        "Files validated: 4/4"
    )
    print(
        "Lease registration/heartbeat expiry: VALIDATED"
    )
    print(
        "Deterministic service resolution: VALIDATED"
    )
    print(
        "Health/enable availability filtering: VALIDATED"
    )
    print(
        "Stale-instance sweeping/recovery: VALIDATED"
    )
    print(
        "Local LoadBalancer binding: VALIDATED"
    )
    print(
        "Discovery-to-balancer health synchronization: VALIDATED"
    )
    print(
        "Protocol service operations: VALIDATED"
    )
    print(
        "Third-party dependencies: 0"
    )


main()
