PARSER_BASE = "libs/data/parsers/"
PROTOCOL_BASE = "libs/protocol/"
LB_BASE = "services/load_balancer/"
CONFIG_BASE = "configs/load_balancer/"

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
            "load balancer config implementation contains forbidden import: "
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


class GoodService:
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
                    "name": self.name,
                    "call": self.calls,
                },
            )
        )


class FailingService:
    def __init__(self):
        self.calls = 0

    def handle(self, request):
        self.calls += 1
        raise RuntimeError(
            "simulated instance failure"
        )


def two_instance_config(
    strategy="round_robin",
):
    return LoadBalancerConfig(
        strategy=strategy,
        max_attempts=2,
        instances=[
            LoadBalancerInstanceConfig(
                "rag-1",
                "rag_service",
                "rag-1",
                max_consecutive_failures=1,
                metadata={
                    "zone": "a",
                },
            ),
            LoadBalancerInstanceConfig(
                "rag-2",
                "rag_service",
                "rag-2",
                max_consecutive_failures=2,
                metadata={
                    "zone": "b",
                },
            ),
        ],
    )


def test_instance_config():
    item = LoadBalancerInstanceConfig(
        "x",
        "service",
        "handler",
        max_consecutive_failures=4,
    )

    eq(
        item.max_consecutive_failures,
        4,
        "instance failure threshold stored",
    )

    expect_error(
        ValueError,
        lambda: (
            LoadBalancerInstanceConfig(
                "",
                "service",
                "handler",
            )
        ),
        "empty instance ID rejected",
    )


def test_defaults():
    config = (
        default_load_balancer_config()
    )

    eq(
        config.strategy,
        "adaptive",
        "default balancing strategy",
    )

    eq(
        len(
            config.instances
        ),
        5,
        "default load-balancer topology has five core service instances",
    )

    eq(
        config.max_attempts,
        2,
        "default retry attempt budget",
    )


def test_codec():
    text = (
        '{"strategy":"least_load",'
        '"max_attempts":3,'
        '"instances":['
        '{"instance_id":"rag-1",'
        '"service_name":"rag_service",'
        '"handler_key":"rag",'
        '"max_consecutive_failures":4,'
        '"healthy":true,'
        '"accepting_requests":true,'
        '"enabled":true}'
        '],'
        '"require_service_redundancy":false,'
        '"metadata":{"profile":"prod"}'
        '}'
    )

    config = (
        LoadBalancerConfigCodec()
        .decode_text(text)
    )

    eq(
        config.strategy,
        "least_load",
        "codec strategy",
    )

    eq(
        config.max_attempts,
        3,
        "codec max attempts",
    )

    eq(
        config.instances[0]
        .handler_key,
        "rag",
        "codec handler key",
    )


def test_redundancy_validation():
    config = LoadBalancerConfig(
        strategy="adaptive",
        instances=[
            LoadBalancerInstanceConfig(
                "only",
                "rag_service",
                "rag",
            ),
        ],
        require_service_redundancy=True,
    )

    result = (
        LoadBalancerConfigValidator()
        .validate(config)
    )

    eq(
        result["valid"],
        False,
        "redundancy requirement detects single instance",
    )

    eq(
        result["errors"][0]["code"],
        "SERVICE_REDUNDANCY_REQUIRED",
        "redundancy validation code",
    )


def test_strategy_factory():
    factory = (
        LoadBalancerConfigFactory()
    )

    check(
        isinstance(
            factory.build_strategy(
                LoadBalancerConfig(
                    strategy="round_robin"
                )
            ),
            RoundRobinStrategy,
        ),
        "round-robin strategy constructed",
    )

    check(
        isinstance(
            factory.build_strategy(
                LoadBalancerConfig(
                    strategy="least_load"
                )
            ),
            LeastLoadStrategy,
        ),
        "least-load strategy constructed",
    )

    check(
        isinstance(
            factory.build_strategy(
                LoadBalancerConfig(
                    strategy="adaptive"
                )
            ),
            AdaptiveStrategy,
        ),
        "adaptive strategy constructed",
    )


def test_round_robin_dispatch():
    one = GoodService("one")
    two = GoodService("two")

    balancer = (
        LoadBalancerConfigFactory()
        .build(
            two_instance_config(
                "round_robin"
            ),
            handlers={
                "rag-1": one,
                "rag-2": two,
            },
        )
    )

    first = balancer.dispatch(
        ServiceRequest(
            "rr-1",
            "rag_service",
            "answer",
        )
    )

    second = balancer.dispatch(
        ServiceRequest(
            "rr-2",
            "rag_service",
            "answer",
        )
    )

    eq(
        first.metadata[
            "load_balancer_instance_id"
        ],
        "rag-1",
        "round robin selects first registered instance",
    )

    eq(
        second.metadata[
            "load_balancer_instance_id"
        ],
        "rag-2",
        "round robin advances deterministically",
    )


def test_retry_and_health_transition():
    bad = FailingService()
    good = GoodService("good")

    balancer = (
        LoadBalancerConfigFactory()
        .build(
            two_instance_config(
                "round_robin"
            ),
            handlers={
                "rag-1": bad,
                "rag-2": good,
            },
        )
    )

    response = balancer.dispatch(
        ServiceRequest(
            "retry-1",
            "rag_service",
            "answer",
        )
    )

    eq(
        response.success,
        True,
        "load balancer retries another configured instance",
    )

    eq(
        response.metadata[
            "load_balancer_instance_id"
        ],
        "rag-2",
        "retry reaches healthy second instance",
    )

    eq(
        response.metadata[
            "load_balancer_attempt"
        ],
        2,
        "retry attempt metadata preserved",
    )

    eq(
        balancer.registry.get(
            "rag-1"
        ).healthy,
        False,
        "configured failure threshold marks failed instance unhealthy",
    )


def test_initial_state():
    good = GoodService("good")

    config = LoadBalancerConfig(
        instances=[
            LoadBalancerInstanceConfig(
                "paused",
                "rag_service",
                "paused",
                accepting_requests=False,
            ),
            LoadBalancerInstanceConfig(
                "unhealthy",
                "rag_service",
                "unhealthy",
                healthy=False,
            ),
            LoadBalancerInstanceConfig(
                "ready",
                "rag_service",
                "ready",
            ),
        ],
    )

    balancer = (
        LoadBalancerConfigFactory()
        .build(
            config,
            handlers={
                "paused": good,
                "unhealthy": good,
                "ready": good,
            },
        )
    )

    eq(
        balancer.registry.get(
            "paused"
        ).available(),
        False,
        "configured paused instance starts unavailable",
    )

    eq(
        balancer.registry.get(
            "unhealthy"
        ).available(),
        False,
        "configured unhealthy instance starts unavailable",
    )

    response = balancer.dispatch(
        ServiceRequest(
            "state-1",
            "rag_service",
            "answer",
        )
    )

    eq(
        response.metadata[
            "load_balancer_instance_id"
        ],
        "ready",
        "balancer skips configured unavailable instances",
    )


def test_least_load_selection():
    one = GoodService("one")
    two = GoodService("two")

    balancer = (
        LoadBalancerConfigFactory()
        .build(
            two_instance_config(
                "least_load"
            ),
            handlers={
                "rag-1": one,
                "rag-2": two,
            },
        )
    )

    first = balancer.registry.get(
        "rag-1"
    )

    first.begin_request()

    try:
        selected = balancer.select(
            "rag_service"
        )

        eq(
            selected.instance_id,
            "rag-2",
            "least-load selects lower active-request instance",
        )

    finally:
        first.finish_success()


def test_missing_handler():
    expect_error(
        KeyError,
        lambda: (
            LoadBalancerConfigFactory()
            .build(
                two_instance_config(),
                handlers={
                    "rag-1": (
                        GoodService(
                            "one"
                        )
                    ),
                },
            )
        ),
        "missing configured instance handler rejected",
    )


def test_service_unavailable():
    balancer = (
        LoadBalancerConfigFactory()
        .build(
            LoadBalancerConfig(
                instances=[]
            ),
            handlers={},
        )
    )

    response = balancer.dispatch(
        ServiceRequest(
            "none",
            "missing_service",
            "status",
        )
    )

    eq(
        response.success,
        False,
        "unregistered service produces protocol failure",
    )

    eq(
        response.error.code,
        "SERVICE_UNAVAILABLE",
        "unregistered service failure code",
    )


def test_health_snapshot():
    balancer = (
        LoadBalancerConfigFactory()
        .build(
            two_instance_config(),
            handlers={
                "rag-1": (
                    GoodService("one")
                ),
                "rag-2": (
                    GoodService("two")
                ),
            },
        )
    )

    snapshot = (
        balancer.health_snapshot()
    )

    eq(
        len(
            snapshot[
                "rag_service"
            ]
        ),
        2,
        "configured topology visible in health snapshot",
    )

    eq(
        snapshot[
            "rag_service"
        ][0][
            "metadata"
        ][
            "zone"
        ],
        "a",
        "instance metadata preserved",
    )


def main():
    test_instance_config()
    test_defaults()
    test_codec()
    test_redundancy_validation()
    test_strategy_factory()
    test_round_robin_dispatch()
    test_retry_and_health_transition()
    test_initial_state()
    test_least_load_selection()
    test_missing_handler()
    test_service_unavailable()
    test_health_snapshot()

    print(
        "LOAD BALANCER CONFIG TEST SUITE: PASS"
    )
    print(
        "Assertions passed:",
        ASSERTIONS,
    )
    print(
        "Files validated: 6/6"
    )
    print(
        "Typed load-balancer topology: VALIDATED"
    )
    print(
        "Handwritten JSON decoding: VALIDATED"
    )
    print(
        "Round-robin/least-load/adaptive strategies: VALIDATED"
    )
    print(
        "Runtime-only handler resolution: VALIDATED"
    )
    print(
        "Retry/failure health transitions: VALIDATED"
    )
    print(
        "Initial pause/unhealthy states: VALIDATED"
    )
    print(
        "Protocol dispatch/unavailable handling: VALIDATED"
    )
    print(
        "Health snapshot integration: VALIDATED"
    )
    print(
        "Third-party dependencies: 0"
    )


main()
