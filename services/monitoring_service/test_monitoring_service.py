SERIAL_BASE = "libs/core/serialization/"
PROTOCOL_BASE = "libs/protocol/"
LB_BASE = "services/load_balancer/"
SERVICE_BASE = "services/monitoring_service/"

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
    "health.py",
    "probe.py",
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
            "monitoring_service implementation contains forbidden import: "
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

    except Exception as exc:
        raise AssertionError(
            message
            + " | wrong exception="
            + repr(exc)
        )

    raise AssertionError(
        message
        + " | expected exception was not raised"
    )


def healthy_handler(
    request,
):
    return (
        ServiceResponse
        .success_response(
            request,
            data={
                "status": {
                    "ready": True,
                    "mode": "ok",
                },
            },
        )
    )


def degraded_handler(
    request,
):
    return (
        ServiceResponse
        .success_response(
            request,
            data={
                "status": {
                    "ready": False,
                    "mode": (
                        "model_not_loaded"
                    ),
                },
            },
        )
    )


def failed_handler(
    request,
):
    return (
        ServiceResponse
        .error_response(
            request,
            ProtocolError(
                code="SERVICE_FAILURE",
                message="Service failed health check",
                retryable=True,
            ),
        )
    )


def exception_handler(
    request,
):
    raise RuntimeError(
        "probe handler crashed"
    )


def invalid_handler(
    request,
):
    return {
        "not": "a response",
    }


def test_probe_healthy():
    probe = ServiceProbe(
        probe_id="rag",
        service_name="rag_service",
        handler=healthy_handler,
        readiness_path=[
            "status",
            "ready",
        ],
    )

    result = probe.execute(
        "probe-1",
        trace_id="trace-1",
    )

    eq(
        result.status,
        "healthy",
        "ready successful service is healthy",
    )

    eq(
        result.readiness,
        True,
        "readiness value captured",
    )

    eq(
        result.response_success,
        True,
        "successful probe response recorded",
    )


def test_probe_degraded():
    probe = ServiceProbe(
        probe_id="inference",
        service_name="inference_service",
        handler=degraded_handler,
        readiness_path=[
            "status",
            "ready",
        ],
    )

    result = probe.execute(
        "probe-2"
    )

    eq(
        result.status,
        "degraded",
        "successful but not-ready service is degraded",
    )

    eq(
        result.readiness,
        False,
        "false readiness preserved",
    )


def test_probe_failures():
    failed = ServiceProbe(
        probe_id="failed",
        service_name="x",
        handler=failed_handler,
    ).execute(
        "probe-3"
    )

    eq(
        failed.status,
        "unhealthy",
        "failed protocol response unhealthy",
    )

    eq(
        failed.error_code,
        "SERVICE_FAILURE",
        "service error code preserved",
    )

    crashed = ServiceProbe(
        probe_id="crashed",
        service_name="y",
        handler=exception_handler,
    ).execute(
        "probe-4"
    )

    eq(
        crashed.status,
        "unhealthy",
        "handler exception unhealthy",
    )

    eq(
        crashed.error_code,
        "RuntimeError",
        "handler exception type reported",
    )

    invalid = ServiceProbe(
        probe_id="invalid",
        service_name="z",
        handler=invalid_handler,
    ).execute(
        "probe-5"
    )

    eq(
        invalid.error_code,
        "INVALID_PROBE_RESPONSE",
        "invalid handler return detected",
    )


def test_manager_required_health():
    manager = MonitoringManager()

    manager.register_probe(
        ServiceProbe(
            "dataset",
            "dataset_service",
            healthy_handler,
            readiness_path=[
                "status",
                "ready",
            ],
        )
    )

    manager.register_probe(
        ServiceProbe(
            "rag",
            "rag_service",
            failed_handler,
            required=True,
        )
    )

    health = manager.health()

    eq(
        health[
            "status"
        ],
        "unhealthy",
        "required unhealthy probe makes system unhealthy",
    )

    eq(
        health[
            "ready"
        ],
        False,
        "unhealthy aggregate not ready",
    )

    eq(
        health[
            "unhealthy_probes"
        ],
        1,
        "unhealthy probe counted",
    )


def test_manager_optional_degradation():
    manager = MonitoringManager()

    manager.register_probe(
        ServiceProbe(
            "required",
            "dataset_service",
            healthy_handler,
            readiness_path=[
                "status",
                "ready",
            ],
            required=True,
        )
    )

    manager.register_probe(
        ServiceProbe(
            "optional",
            "inference_service",
            degraded_handler,
            readiness_path=[
                "status",
                "ready",
            ],
            required=False,
        )
    )

    health = manager.health()

    eq(
        health[
            "status"
        ],
        "degraded",
        "optional problem degrades aggregate",
    )

    eq(
        health[
            "ready"
        ],
        True,
        "degraded system remains ready",
    )


def test_cached_snapshot_without_probe_run():
    manager = MonitoringManager()

    manager.register_probe(
        ServiceProbe(
            "a",
            "a_service",
            healthy_handler,
            readiness_path=[
                "status",
                "ready",
            ],
        )
    )

    first = manager.health(
        run_probes=True
    )

    second = manager.health(
        run_probes=False
    )

    eq(
        second[
            "executed_probe_count"
        ],
        1,
        "cached snapshot exposes prior result",
    )

    eq(
        second[
            "probes"
        ],
        first[
            "probes"
        ],
        "cached health result stable",
    )


def test_probe_registry():
    manager = MonitoringManager()

    probe = ServiceProbe(
        "a",
        "a_service",
        healthy_handler,
    )

    manager.register_probe(
        probe
    )

    eq(
        manager.get_probe(
            "a"
        ),
        probe,
        "get registered probe",
    )

    eq(
        manager.list_probes()[
            0
        ][
            "probe_id"
        ],
        "a",
        "probe list stable",
    )

    expect_error(
        ValueError,
        lambda: manager.register_probe(
            probe
        ),
        "duplicate probe rejected",
    )

    removed = manager.deregister_probe(
        "a"
    )

    eq(
        removed,
        probe,
        "deregister returns probe",
    )

    expect_error(
        KeyError,
        lambda: manager.get_probe(
            "a"
        ),
        "removed probe unavailable",
    )


def build_load_balancer():
    balancer = LoadBalancer()

    balancer.register(
        ServiceInstance(
            "rag-1",
            "rag_service",
            healthy_handler,
        )
    )

    balancer.register(
        ServiceInstance(
            "rag-2",
            "rag_service",
            healthy_handler,
        )
    )

    balancer.register(
        ServiceInstance(
            "retrieval-1",
            "retrieval_service",
            healthy_handler,
        )
    )

    return balancer


def test_load_balancer_healthy():
    balancer = build_load_balancer()

    manager = MonitoringManager(
        load_balancer=balancer
    )

    status = (
        manager
        .load_balancer_status()
    )

    eq(
        status[
            "status"
        ],
        "healthy",
        "all available instances healthy",
    )

    eq(
        status[
            "total_instances"
        ],
        3,
        "LB total instance count",
    )

    eq(
        status[
            "available_instances"
        ],
        3,
        "LB available instance count",
    )


def test_load_balancer_degraded():
    balancer = build_load_balancer()

    balancer.registry.get(
        "rag-2"
    ).pause()

    manager = MonitoringManager(
        load_balancer=balancer
    )

    status = (
        manager
        .load_balancer_status()
    )

    eq(
        status[
            "status"
        ],
        "degraded",
        "partial instance availability degrades LB",
    )

    eq(
        status[
            "paused_instances"
        ],
        1,
        "paused instance counted",
    )

    eq(
        status[
            "services"
        ][
            "rag_service"
        ][
            "available_instances"
        ],
        1,
        "service still has one available instance",
    )


def test_load_balancer_unhealthy_service():
    balancer = build_load_balancer()

    balancer.registry.get(
        "retrieval-1"
    ).mark_unhealthy()

    manager = MonitoringManager(
        load_balancer=balancer
    )

    status = (
        manager
        .load_balancer_status()
    )

    eq(
        status[
            "status"
        ],
        "unhealthy",
        "service with zero available instances makes LB unhealthy",
    )

    eq(
        status[
            "services"
        ][
            "retrieval_service"
        ][
            "status"
        ],
        "unhealthy",
        "per-service LB health reported",
    )

    health = manager.health()

    eq(
        health[
            "status"
        ],
        "unhealthy",
        "LB outage propagates to aggregate health",
    )


def test_load_accounting():
    balancer = build_load_balancer()

    instance = balancer.registry.get(
        "rag-1"
    )

    instance.begin_request()
    instance.finish_success()

    instance.begin_request()
    instance.finish_failure()

    status = MonitoringManager(
        load_balancer=balancer
    ).load_balancer_status()

    eq(
        status[
            "total_requests"
        ],
        2,
        "LB total request accounting",
    )

    eq(
        status[
            "failed_requests"
        ],
        1,
        "LB failure accounting",
    )


def test_service_health_endpoint():
    manager = MonitoringManager()

    manager.register_probe(
        ServiceProbe(
            "dataset",
            "dataset_service",
            healthy_handler,
            readiness_path=[
                "status",
                "ready",
            ],
        )
    )

    service = MonitoringService(
        manager
    )

    response = service.handle(
        ServiceRequest(
            "h1",
            "monitoring_service",
            "health",
            trace_id="trace-health",
        )
    )

    eq(
        response.success,
        True,
        "monitoring health endpoint succeeds",
    )

    eq(
        response.data[
            "health"
        ][
            "status"
        ],
        "healthy",
        "health endpoint aggregate",
    )

    eq(
        response.trace_id,
        "trace-health",
        "health trace preserved",
    )


def test_service_probe_and_list():
    manager = MonitoringManager()

    manager.register_probe(
        ServiceProbe(
            "rag",
            "rag_service",
            degraded_handler,
            readiness_path=[
                "status",
                "ready",
            ],
        )
    )

    service = MonitoringService(
        manager
    )

    listed = service.handle(
        ServiceRequest(
            "l1",
            "monitoring_service",
            "list_probes",
        )
    )

    eq(
        listed.data[
            "count"
        ],
        1,
        "service lists probes",
    )

    probed = service.handle(
        ServiceRequest(
            "p1",
            "monitoring_service",
            "probe",
            payload={
                "probe_id": "rag",
            },
        )
    )

    eq(
        probed.data[
            "probe"
        ][
            "status"
        ],
        "degraded",
        "service runs specific probe",
    )


def test_protocol_round_trip():
    manager = MonitoringManager()

    manager.register_probe(
        ServiceProbe(
            "dataset",
            "dataset_service",
            healthy_handler,
            readiness_path=[
                "status",
                "ready",
            ],
        )
    )

    service = MonitoringService(
        manager
    )

    codec = ProtocolCodec()

    request = ServiceRequest(
        "protocol-health",
        "monitoring_service",
        "health",
        payload={
            "run_probes": True,
        },
        trace_id="trace-monitoring",
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
        "monitoring health survives protocol codec",
    )

    eq(
        response.trace_id,
        "trace-monitoring",
        "monitoring trace preserved",
    )

    eq(
        response.data[
            "health"
        ][
            "healthy_probes"
        ],
        1,
        "protocol health probe count",
    )


def test_api_gateway_contract():
    service = MonitoringService(
        MonitoringManager()
    )

    response = service.handle(
        ServiceRequest(
            "gateway-health",
            "monitoring_service",
            "health",
        )
    )

    eq(
        response.success,
        True,
        "API gateway default monitoring_service.health contract implemented",
    )

    eq(
        response.data[
            "health"
        ][
            "ready"
        ],
        True,
        "empty monitoring core defaults ready",
    )


def test_errors():
    service = MonitoringService(
        MonitoringManager()
    )

    missing = service.handle(
        ServiceRequest(
            "m",
            "monitoring_service",
            "probe",
            payload={
                "probe_id": "missing",
            },
        )
    )

    eq(
        missing.error.code,
        "NOT_FOUND",
        "missing probe maps to NOT_FOUND",
    )

    wrong = service.handle(
        ServiceRequest(
            "w",
            "rag_service",
            "health",
        )
    )

    eq(
        wrong.error.code,
        "INVALID_REQUEST",
        "wrong target service rejected",
    )

    unsupported = service.handle(
        ServiceRequest(
            "u",
            "monitoring_service",
            "unknown",
        )
    )

    eq(
        unsupported.error.code,
        "INVALID_REQUEST",
        "unsupported operation rejected",
    )

    expect_error(
        TypeError,
        lambda: service.handle(
            {}
        ),
        "non-ServiceRequest rejected",
    )


def test_validation():
    expect_error(
        ValueError,
        lambda: ServiceProbe(
            "",
            "x",
            healthy_handler,
        ),
        "empty probe ID rejected",
    )

    expect_error(
        TypeError,
        lambda: ServiceProbe(
            "x",
            "x",
            None,
        ),
        "non-callable probe handler rejected",
    )

    class InvalidBalancer:
        pass

    manager = MonitoringManager(
        load_balancer=(
            InvalidBalancer()
        )
    )

    expect_error(
        TypeError,
        lambda: manager.load_balancer_status(),
        "invalid load balancer rejected",
    )


def main():
    test_probe_healthy()
    test_probe_degraded()
    test_probe_failures()
    test_manager_required_health()
    test_manager_optional_degradation()
    test_cached_snapshot_without_probe_run()
    test_probe_registry()
    test_load_balancer_healthy()
    test_load_balancer_degraded()
    test_load_balancer_unhealthy_service()
    test_load_accounting()
    test_service_health_endpoint()
    test_service_probe_and_list()
    test_protocol_round_trip()
    test_api_gateway_contract()
    test_errors()
    test_validation()

    print(
        "MONITORING SERVICE TEST SUITE: PASS"
    )
    print(
        "Assertions passed:",
        ASSERTIONS,
    )
    print(
        "Files validated: 4/4"
    )
    print(
        "Protocol-aware active service probes: VALIDATED"
    )
    print(
        "Healthy/degraded/unhealthy aggregation: VALIDATED"
    )
    print(
        "Required/optional readiness semantics: VALIDATED"
    )
    print(
        "Load-balancer instance health/accounting: VALIDATED"
    )
    print(
        "Partial/zero-availability detection: VALIDATED"
    )
    print(
        "Cached monitoring snapshots: VALIDATED"
    )
    print(
        "API gateway health contract: VALIDATED"
    )
    print(
        "Protocol service operations: VALIDATED"
    )
    print(
        "Third-party dependencies: 0"
    )


main()
