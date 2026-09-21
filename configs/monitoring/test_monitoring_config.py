PARSER_BASE = "libs/data/parsers/"
PROTOCOL_BASE = "libs/protocol/"
LB_BASE = "services/load_balancer/"
MON_BASE = "services/monitoring_service/"
CONFIG_BASE = "configs/monitoring/"

namespace = {
    "__builtins__": __builtins__,
}

groups = [
    (
        PARSER_BASE,
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
        LB_BASE,
        [
            "instance.py",
            "registry.py",
            "strategies.py",
            "load_balancer.py",
        ],
    ),
    (
        MON_BASE,
        [
            "health.py",
            "probe.py",
            "manager.py",
            "service.py",
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
    "config.py",
    "defaults.py",
    "codec.py",
    "validator.py",
    "factory.py",
]:
    path = CONFIG_BASE + filename

    source = open(
        path,
        "r",
        encoding="utf-8",
    ).read()

    if "import " in source:
        raise AssertionError(
            "monitoring config implementation contains forbidden import: "
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
        + repr(expected),
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


class StatusService:
    def __init__(
        self,
        service_name,
        ready=True,
        succeed=True,
    ):
        self.service_name = (
            service_name
        )
        self.ready = ready
        self.succeed = succeed
        self.calls = 0

    def handle(
        self,
        request,
    ):
        self.calls += 1

        if not self.succeed:
            return (
                ServiceResponse
                .error_response(
                    request,
                    ProtocolError(
                        code=(
                            "SERVICE_NOT_READY"
                        ),
                        message=(
                            "simulated failure"
                        ),
                        retryable=False,
                    ),
                )
            )

        return (
            ServiceResponse
            .success_response(
                request,
                data={
                    "status": {
                        "ready": (
                            self.ready
                        ),
                        "service": (
                            self.service_name
                        ),
                    },
                },
            )
        )


def sample_config(
    attach_load_balancer=False,
):
    return MonitoringConfig(
        probes=[
            MonitoringProbeConfig(
                probe_id="rag-ready",
                service_name=(
                    "rag_service"
                ),
                operation="status",
                required=True,
                readiness_path=[
                    "status",
                    "ready",
                ],
                metadata={
                    "layer": "rag",
                },
            ),
            MonitoringProbeConfig(
                probe_id=(
                    "conversation-ready"
                ),
                service_name=(
                    "conversation_service"
                ),
                operation="status",
                required=False,
                readiness_path=[
                    "status",
                    "ready",
                ],
            ),
        ],
        attach_load_balancer=(
            attach_load_balancer
        ),
        metadata={
            "profile": "runtime",
        },
    )


def handlers(
    rag_ready=True,
    conversation_ready=True,
):
    return {
        "rag_service": (
            StatusService(
                "rag_service",
                ready=rag_ready,
            )
        ),
        "conversation_service": (
            StatusService(
                "conversation_service",
                ready=(
                    conversation_ready
                ),
            )
        ),
    }


def success_handler(
    name,
):
    def handler(
        request,
    ):
        return (
            ServiceResponse
            .success_response(
                request,
                data={
                    "instance": name,
                },
            )
        )

    return handler


def test_probe_config():
    probe = MonitoringProbeConfig(
        "x",
        "rag_service",
        readiness_path=[
            "status",
            "ready",
        ],
    )

    eq(
        probe.readiness_path,
        [
            "status",
            "ready",
        ],
        "probe readiness path stored",
    )

    expect_error(
        ValueError,
        lambda: MonitoringProbeConfig(
            "",
            "service",
        ),
        "empty probe ID rejected",
    )


def test_defaults():
    config = (
        default_monitoring_config()
    )

    eq(
        len(
            config.probes
        ),
        5,
        "default monitoring topology has five core probes",
    )

    eq(
        config.attach_load_balancer,
        True,
        "default monitoring attaches load balancer",
    )

    eq(
        config.probe_map()[
            "rag-ready"
        ].required,
        True,
        "RAG readiness is required by default",
    )


def test_codec():
    text = (
        '{"probes":['
        '{"probe_id":"rag",'
        '"service_name":"rag_service",'
        '"operation":"status",'
        '"payload":{"verbose":false},'
        '"required":true,'
        '"readiness_path":["status","ready"],'
        '"enabled":true}'
        '],'
        '"attach_load_balancer":false,'
        '"metadata":{"profile":"prod"}'
        '}'
    )

    config = (
        MonitoringConfigCodec()
        .decode_text(
            text
        )
    )

    eq(
        config.probes[
            0
        ].service_name,
        "rag_service",
        "codec service name",
    )

    eq(
        config.probes[
            0
        ].payload[
            "verbose"
        ],
        False,
        "codec probe payload",
    )

    eq(
        config.metadata[
            "profile"
        ],
        "prod",
        "codec metadata",
    )


def test_validator():
    config = MonitoringConfig(
        probes=[
            MonitoringProbeConfig(
                "basic",
                "service",
            ),
        ],
    )

    result = (
        MonitoringConfigValidator()
        .validate(
            config
        )
    )

    codes = [
        item[
            "code"
        ]
        for item
        in result[
            "warnings"
        ]
    ]

    check(
        "PROBE_WITHOUT_READINESS_PATH"
        in codes,
        "success-only probe warned",
    )


def test_healthy_manager():
    hs = handlers()

    manager = (
        MonitoringConfigFactory()
        .build_manager(
            sample_config(),
            hs,
        )
    )

    health = manager.health()

    eq(
        health[
            "status"
        ],
        "healthy",
        "all ready probes produce healthy status",
    )

    eq(
        health[
            "ready"
        ],
        True,
        "healthy monitoring state is ready",
    )

    eq(
        health[
            "healthy_probes"
        ],
        2,
        "all configured probes executed",
    )


def test_required_degraded():
    hs = handlers(
        rag_ready=False,
    )

    manager = (
        MonitoringConfigFactory()
        .build_manager(
            sample_config(),
            hs,
        )
    )

    health = manager.health()

    eq(
        health[
            "status"
        ],
        "degraded",
        "required readiness false produces degraded status",
    )

    eq(
        health[
            "ready"
        ],
        True,
        "degraded readiness remains serviceable",
    )


def test_required_unhealthy():
    config = MonitoringConfig(
        probes=[
            MonitoringProbeConfig(
                "rag",
                "rag_service",
                required=True,
                readiness_path=[
                    "status",
                    "ready",
                ],
            ),
        ],
    )

    service = StatusService(
        "rag_service",
        succeed=False,
    )

    manager = (
        MonitoringConfigFactory()
        .build_manager(
            config,
            {
                "rag_service": service,
            },
        )
    )

    health = manager.health()

    eq(
        health[
            "status"
        ],
        "unhealthy",
        "required failed probe produces unhealthy status",
    )

    eq(
        health[
            "ready"
        ],
        False,
        "required failed probe disables readiness",
    )


def test_probe_specific_handler():
    service_level = StatusService(
        "rag_service",
        ready=False,
    )

    probe_level = StatusService(
        "rag_service",
        ready=True,
    )

    manager = (
        MonitoringConfigFactory()
        .build_manager(
            MonitoringConfig(
                probes=[
                    MonitoringProbeConfig(
                        "rag-ready",
                        "rag_service",
                        readiness_path=[
                            "status",
                            "ready",
                        ],
                    ),
                ],
            ),
            {
                "rag_service": (
                    service_level
                ),
                "rag-ready": (
                    probe_level
                ),
            },
        )
    )

    result = manager.run_probe(
        "rag-ready"
    )

    eq(
        result.status,
        "healthy",
        "probe-specific handler overrides service handler",
    )

    eq(
        probe_level.calls,
        1,
        "probe-specific handler invoked",
    )

    eq(
        service_level.calls,
        0,
        "fallback service handler not invoked",
    )


def test_missing_handler_boundary():
    expect_error(
        KeyError,
        lambda: (
            MonitoringConfigFactory()
            .build_manager(
                sample_config(),
                {},
            )
        ),
        "missing runtime probe handler rejected",
    )


def test_load_balancer_integration():
    lb = LoadBalancer()

    lb.register(
        ServiceInstance(
            "rag-1",
            "rag_service",
            success_handler(
                "rag-1"
            ),
        )
    )

    lb.register(
        ServiceInstance(
            "rag-2",
            "rag_service",
            success_handler(
                "rag-2"
            ),
        )
    )

    manager = (
        MonitoringConfigFactory()
        .build_manager(
            sample_config(
                attach_load_balancer=True
            ),
            handlers(),
            load_balancer=lb,
        )
    )

    healthy = manager.health()

    eq(
        healthy[
            "load_balancer"
        ][
            "status"
        ],
        "healthy",
        "fully available configured load balancer healthy",
    )

    lb.registry.mark_unhealthy(
        "rag-1"
    )

    degraded = manager.health()

    eq(
        degraded[
            "status"
        ],
        "degraded",
        "partial load-balancer capacity degrades overall health",
    )

    lb.registry.mark_unhealthy(
        "rag-2"
    )

    unhealthy = manager.health()

    eq(
        unhealthy[
            "status"
        ],
        "unhealthy",
        "zero available instances makes monitoring unhealthy",
    )

    eq(
        unhealthy[
            "ready"
        ],
        False,
        "zero load-balancer capacity disables readiness",
    )


def test_lb_required_boundary():
    expect_error(
        ValueError,
        lambda: (
            MonitoringConfigFactory()
            .build_manager(
                sample_config(
                    attach_load_balancer=True
                ),
                handlers(),
                load_balancer=None,
            )
        ),
        "required load balancer dependency enforced",
    )


def test_service_creation():
    service = (
        MonitoringConfigFactory()
        .build_service(
            sample_config(),
            handlers(),
        )
    )

    check(
        isinstance(
            service,
            MonitoringService,
        ),
        "factory creates MonitoringService",
    )

    response = service.handle(
        ServiceRequest(
            "mon-health",
            "monitoring_service",
            "health",
        )
    )

    eq(
        response.success,
        True,
        "configured monitoring service responds",
    )

    eq(
        response.data[
            "health"
        ][
            "status"
        ],
        "healthy",
        "configured monitoring service reports health",
    )

    listing = service.handle(
        ServiceRequest(
            "mon-list",
            "monitoring_service",
            "list_probes",
        )
    )

    eq(
        listing.data[
            "count"
        ],
        2,
        "configured monitoring service exposes probes",
    )


def test_disabled_probe():
    config = MonitoringConfig(
        probes=[
            MonitoringProbeConfig(
                "on",
                "rag_service",
                readiness_path=[
                    "status",
                    "ready",
                ],
            ),
            MonitoringProbeConfig(
                "off",
                "conversation_service",
                enabled=False,
                readiness_path=[
                    "status",
                    "ready",
                ],
            ),
        ],
    )

    manager = (
        MonitoringConfigFactory()
        .build_manager(
            config,
            {
                "rag_service": (
                    StatusService(
                        "rag_service"
                    )
                ),
            },
        )
    )

    eq(
        [
            item[
                "probe_id"
            ]
            for item
            in manager.list_probes()
        ],
        [
            "on",
        ],
        "disabled monitoring probe excluded from runtime manager",
    )


def main():
    test_probe_config()
    test_defaults()
    test_codec()
    test_validator()
    test_healthy_manager()
    test_required_degraded()
    test_required_unhealthy()
    test_probe_specific_handler()
    test_missing_handler_boundary()
    test_load_balancer_integration()
    test_lb_required_boundary()
    test_service_creation()
    test_disabled_probe()

    print(
        "MONITORING CONFIG TEST SUITE: PASS"
    )
    print(
        "Assertions passed:",
        ASSERTIONS,
    )
    print(
        "Files validated: 6/6"
    )
    print(
        "Typed service-probe topology: VALIDATED"
    )
    print(
        "Handwritten JSON decoding: VALIDATED"
    )
    print(
        "Runtime handler resolution: VALIDATED"
    )
    print(
        "Required/optional readiness semantics: VALIDATED"
    )
    print(
        "Healthy/degraded/unhealthy aggregation: VALIDATED"
    )
    print(
        "Real LoadBalancer health integration: VALIDATED"
    )
    print(
        "MonitoringService generation: VALIDATED"
    )
    print(
        "Third-party dependencies: 0"
    )


main()
