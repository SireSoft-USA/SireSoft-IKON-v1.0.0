PARSER_BASE = "libs/data/parsers/"
PROTOCOL_BASE = "libs/protocol/"
LB_BASE = "services/load_balancer/"
DISCOVERY_BASE = "services/service_discovery/"
CONFIG_BASE = "configs/service_discovery/"

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
        DISCOVERY_BASE,
        [
            "descriptor.py",
            "registry.py",
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
    "instance.py",
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
            "service discovery config implementation contains forbidden import: "
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

globals().update(namespace)

ASSERTIONS = 0


def check(condition, message):
    global ASSERTIONS
    ASSERTIONS += 1

    if not condition:
        raise AssertionError(message)


def eq(actual, expected, message):
    check(
        actual == expected,
        message
        + " | got="
        + repr(actual)
        + " expected="
        + repr(expected),
    )


def expect_error(error_type, fn, message):
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
    def __init__(self, name):
        self.name = name
        self.calls = 0

    def handle(self, request):
        self.calls += 1

        return (
            ServiceResponse
            .success_response(
                request,
                data={
                    "service": self.name,
                    "operation": (
                        request.operation
                    ),
                },
            )
        )


def sample_config():
    return ServiceDiscoveryConfig(
        instances=[
            DiscoveryInstanceConfig(
                instance_id="rag-local-1",
                service_name="rag_service",
                endpoint=(
                    "local://rag_service/"
                    "rag-local-1"
                ),
                lease_seconds=10,
                local_handler_key=(
                    "rag-handler"
                ),
                max_consecutive_failures=2,
                metadata={
                    "zone": "local",
                },
            ),
            DiscoveryInstanceConfig(
                instance_id="rag-remote-1",
                service_name="rag_service",
                endpoint=(
                    "http://rag.internal:8080"
                ),
                lease_seconds=20,
                metadata={
                    "zone": "remote",
                },
            ),
            DiscoveryInstanceConfig(
                instance_id="disabled-1",
                service_name=(
                    "retrieval_service"
                ),
                endpoint=(
                    "http://retrieval.invalid"
                ),
                enabled=False,
            ),
        ],
        attach_load_balancer=True,
    )


def handlers():
    return {
        "rag-handler": (
            EchoService(
                "rag_service"
            )
        ),
    }


def test_instance_config():
    instance = DiscoveryInstanceConfig(
        "one",
        "svc",
        "http://svc",
        lease_seconds=15,
    )

    eq(
        instance.local(),
        False,
        "remote instance identified",
    )

    expect_error(
        ValueError,
        lambda: DiscoveryInstanceConfig(
            "",
            "svc",
            "http://svc",
        ),
        "empty discovery instance ID rejected",
    )


def test_defaults():
    config = (
        default_service_discovery_config()
    )

    eq(
        len(config.instances),
        5,
        "default discovery topology includes five core services",
    )

    eq(
        config.attach_load_balancer,
        True,
        "default discovery topology attaches load balancer",
    )

    check(
        all(
            item.local()
            for item
            in config.instances
        ),
        "default discovery topology uses local runtime bindings",
    )


def test_codec():
    text = (
        '{"instances":['
        '{"instance_id":"rag-1",'
        '"service_name":"rag_service",'
        '"endpoint":"local://rag_service/rag-1",'
        '"lease_seconds":30,'
        '"local_handler_key":"rag",'
        '"max_consecutive_failures":4,'
        '"enabled":true,'
        '"metadata":{"zone":"a"}}'
        '],'
        '"attach_load_balancer":true,'
        '"metadata":{"profile":"prod"}'
        '}'
    )

    config = (
        ServiceDiscoveryConfigCodec()
        .decode_text(text)
    )

    eq(
        config.instances[0]
        .lease_seconds,
        30,
        "codec discovery lease",
    )

    eq(
        config.instances[0]
        .local_handler_key,
        "rag",
        "codec local handler key",
    )

    eq(
        config.metadata["profile"],
        "prod",
        "codec metadata",
    )


def test_validator():
    config = ServiceDiscoveryConfig(
        instances=[
            DiscoveryInstanceConfig(
                "local",
                "svc",
                "local://svc/local",
                local_handler_key="svc",
            ),
        ],
        attach_load_balancer=False,
    )

    result = (
        ServiceDiscoveryConfigValidator()
        .validate(config)
    )

    eq(
        result["valid"],
        False,
        "local discovery instance requires load balancer",
    )

    eq(
        result["errors"][0]["code"],
        "LOCAL_INSTANCE_WITHOUT_LOAD_BALANCER",
        "local/load-balancer validation code",
    )


def test_initialize():
    lb = LoadBalancer()
    hs = handlers()

    result = (
        ServiceDiscoveryConfigFactory()
        .initialize(
            sample_config(),
            now=100,
            handlers=hs,
            load_balancer=lb,
        )
    )

    manager = result["manager"]

    eq(
        result["registered_count"],
        2,
        "disabled discovery instance excluded",
    )

    eq(
        manager.registry.count(),
        2,
        "configured instances registered",
    )

    eq(
        manager.registry.get(
            "rag-local-1"
        ).local_bound,
        True,
        "configured local instance bound to load balancer",
    )

    eq(
        lb.registry.count(
            "rag_service"
        ),
        1,
        "only local discovery instance enters local load balancer",
    )


def test_resolution_and_staleness():
    lb = LoadBalancer()

    manager = (
        ServiceDiscoveryConfigFactory()
        .initialize(
            sample_config(),
            now=100,
            handlers=handlers(),
            load_balancer=lb,
        )[
            "manager"
        ]
    )

    fresh = manager.resolve(
        "rag_service",
        now=105,
    )

    eq(
        fresh["count"],
        2,
        "fresh local and remote instances resolve",
    )

    stale = manager.resolve(
        "rag_service",
        now=110,
    )

    eq(
        stale["count"],
        1,
        "local instance expires at exact lease boundary",
    )

    eq(
        stale["instances"][0][
            "instance_id"
        ],
        "rag-remote-1",
        "longer remote lease remains available",
    )

    eq(
        lb.registry.get(
            "rag-local-1"
        ).healthy,
        False,
        "stale local discovery health synchronizes to load balancer",
    )


def test_heartbeat_recovery():
    lb = LoadBalancer()

    manager = (
        ServiceDiscoveryConfigFactory()
        .initialize(
            sample_config(),
            now=100,
            handlers=handlers(),
            load_balancer=lb,
        )[
            "manager"
        ]
    )

    manager.sweep_stale(
        110
    )

    manager.heartbeat(
        "rag-local-1",
        111,
    )

    descriptor = (
        manager.registry.get(
            "rag-local-1"
        )
    )

    eq(
        descriptor.available(
            111
        ),
        True,
        "heartbeat restores discovered instance",
    )

    eq(
        lb.registry.get(
            "rag-local-1"
        ).healthy,
        True,
        "heartbeat restores load-balancer health",
    )


def test_dispatch_through_bound_instance():
    lb = LoadBalancer()
    hs = handlers()

    (
        ServiceDiscoveryConfigFactory()
        .initialize(
            sample_config(),
            now=100,
            handlers=hs,
            load_balancer=lb,
        )
    )

    response = lb.dispatch(
        ServiceRequest(
            "rag-call",
            "rag_service",
            "answer",
        )
    )

    eq(
        response.success,
        True,
        "bound discovery handler dispatches through load balancer",
    )

    eq(
        response.data["service"],
        "rag_service",
        "bound handler receives routed request",
    )

    eq(
        response.metadata[
            "load_balancer_instance_id"
        ],
        "rag-local-1",
        "load balancer dispatch selects discovered local instance",
    )


def test_disable_sync():
    lb = LoadBalancer()

    manager = (
        ServiceDiscoveryConfigFactory()
        .initialize(
            sample_config(),
            now=100,
            handlers=handlers(),
            load_balancer=lb,
        )[
            "manager"
        ]
    )

    manager.disable(
        "rag-local-1"
    )

    instance = lb.registry.get(
        "rag-local-1"
    )

    eq(
        instance.healthy,
        False,
        "discovery disable marks local LB instance unhealthy",
    )

    eq(
        instance.accepting_requests,
        False,
        "discovery disable pauses local LB instance",
    )

    manager.enable(
        "rag-local-1"
    )

    eq(
        instance.healthy,
        True,
        "discovery enable restores local LB instance health",
    )

    eq(
        instance.accepting_requests,
        True,
        "discovery enable resumes local LB instance",
    )


def test_missing_handler():
    expect_error(
        KeyError,
        lambda: (
            ServiceDiscoveryConfigFactory()
            .initialize(
                sample_config(),
                now=100,
                handlers={},
                load_balancer=(
                    LoadBalancer()
                ),
            )
        ),
        "missing local runtime handler rejected",
    )


def test_remote_without_lb():
    config = ServiceDiscoveryConfig(
        instances=[
            DiscoveryInstanceConfig(
                "remote-1",
                "remote_service",
                "http://remote:9000",
                lease_seconds=30,
            ),
        ],
        attach_load_balancer=False,
    )

    result = (
        ServiceDiscoveryConfigFactory()
        .initialize(
            config,
            now=5,
            handlers={},
        )
    )

    eq(
        result["manager"]
        .status(5)[
            "load_balancer_attached"
        ],
        False,
        "remote-only discovery works without load balancer",
    )

    eq(
        result["manager"]
        .resolve(
            "remote_service",
            5,
        )[
            "count"
        ],
        1,
        "remote-only discovered instance resolves",
    )


def test_service_creation():
    lb = LoadBalancer()

    service = (
        ServiceDiscoveryConfigFactory()
        .build_service(
            sample_config(),
            now=100,
            handlers=handlers(),
            load_balancer=lb,
        )
    )

    check(
        isinstance(
            service,
            ServiceDiscoveryService,
        ),
        "factory creates ServiceDiscoveryService",
    )

    status = service.handle(
        ServiceRequest(
            "disc-status",
            "service_discovery",
            "status",
            payload={
                "now": 105,
            },
        )
    )

    eq(
        status.success,
        True,
        "configured discovery service responds",
    )

    eq(
        status.data["status"][
            "instance_count"
        ],
        2,
        "configured discovery service exposes instance count",
    )

    resolution = service.handle(
        ServiceRequest(
            "disc-resolve",
            "service_discovery",
            "resolve",
            payload={
                "service_name": (
                    "rag_service"
                ),
                "now": 105,
            },
        )
    )

    eq(
        resolution.data[
            "resolution"
        ][
            "count"
        ],
        2,
        "configured discovery service resolves configured instances",
    )


def main():
    test_instance_config()
    test_defaults()
    test_codec()
    test_validator()
    test_initialize()
    test_resolution_and_staleness()
    test_heartbeat_recovery()
    test_dispatch_through_bound_instance()
    test_disable_sync()
    test_missing_handler()
    test_remote_without_lb()
    test_service_creation()

    print(
        "SERVICE DISCOVERY CONFIG TEST SUITE: PASS"
    )
    print(
        "Assertions passed:",
        ASSERTIONS,
    )
    print(
        "Files validated: 6/6"
    )
    print(
        "Typed discovery topology: VALIDATED"
    )
    print(
        "Handwritten JSON decoding: VALIDATED"
    )
    print(
        "Lease registration/staleness: VALIDATED"
    )
    print(
        "Heartbeat recovery: VALIDATED"
    )
    print(
        "Runtime-only local handler binding: VALIDATED"
    )
    print(
        "LoadBalancer health synchronization: VALIDATED"
    )
    print(
        "Remote-only discovery mode: VALIDATED"
    )
    print(
        "ServiceDiscoveryService generation: VALIDATED"
    )
    print(
        "Third-party dependencies: 0"
    )


main()
