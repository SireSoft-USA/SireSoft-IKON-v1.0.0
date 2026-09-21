SERIAL_BASE = "libs/core/serialization/"
PROTOCOL_BASE = "libs/protocol/"
LB_BASE = "services/load_balancer/"

namespace = {
    "__builtins__": __builtins__,
}

for filename in [
    "binary_writer.py",
    "binary_reader.py",
    "checksum.py",
]:
    path = SERIAL_BASE + filename

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
    "error.py",
    "message.py",
    "request.py",
    "response.py",
    "validator.py",
    "codec.py",
]:
    path = PROTOCOL_BASE + filename

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
    "registry.py",
    "strategies.py",
    "load_balancer.py",
]:
    path = LB_BASE + filename

    source = open(
        path,
        "r",
        encoding="utf-8",
    ).read()

    if "import " in source:
        raise AssertionError(
            "load_balancer implementation contains forbidden import: "
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


def success_handler(
    instance_name,
):
    def handler(request):
        return ServiceResponse.success_response(
            request,
            data={
                "instance": instance_name,
                "operation": request.operation,
            },
        )

    return handler


def test_instance_lifecycle():
    instance = ServiceInstance(
        "rag-1",
        "rag_service",
        success_handler("rag-1"),
        max_consecutive_failures=2,
    )

    check(
        instance.available(),
        "new instance available",
    )

    instance.begin_request()
    eq(
        instance.active_requests,
        1,
        "begin increments active",
    )

    instance.finish_success()

    eq(
        instance.active_requests,
        0,
        "success decrements active",
    )

    eq(
        instance.successful_requests,
        1,
        "success counter",
    )

    instance.pause()

    check(
        not instance.available(),
        "paused instance unavailable",
    )

    instance.resume()

    check(
        instance.available(),
        "resumed instance available",
    )


def test_failure_health_threshold():
    instance = ServiceInstance(
        "x",
        "service",
        success_handler("x"),
        max_consecutive_failures=2,
    )

    instance.begin_request()
    instance.finish_failure()

    check(
        instance.healthy,
        "first failure below threshold remains healthy",
    )

    instance.begin_request()
    instance.finish_failure()

    check(
        not instance.healthy,
        "failure threshold marks unhealthy",
    )

    instance.mark_healthy()

    check(
        instance.healthy,
        "manual health recovery",
    )

    eq(
        instance.consecutive_failures,
        0,
        "health recovery resets failure count",
    )


def test_registry():
    registry = ServiceRegistry()

    first = ServiceInstance(
        "retrieval-1",
        "retrieval_service",
        success_handler("retrieval-1"),
    )

    second = ServiceInstance(
        "retrieval-2",
        "retrieval_service",
        success_handler("retrieval-2"),
    )

    registry.register(
        first
    ).register(
        second
    )

    eq(
        registry.count(
            "retrieval_service"
        ),
        2,
        "registry service count",
    )

    eq(
        [
            item.instance_id
            for item
            in registry.instances(
                "retrieval_service"
            )
        ],
        [
            "retrieval-1",
            "retrieval-2",
        ],
        "registry preserves order",
    )

    registry.mark_unhealthy(
        "retrieval-1"
    )

    eq(
        [
            item.instance_id
            for item
            in registry.instances(
                "retrieval_service",
                available_only=True,
            )
        ],
        [
            "retrieval-2",
        ],
        "available registry filtering",
    )

    removed = registry.deregister(
        "retrieval-1"
    )

    eq(
        removed.instance_id,
        "retrieval-1",
        "deregister returns instance",
    )


def test_round_robin():
    instances = [
        ServiceInstance(
            "a",
            "service",
            success_handler("a"),
        ),
        ServiceInstance(
            "b",
            "service",
            success_handler("b"),
        ),
        ServiceInstance(
            "c",
            "service",
            success_handler("c"),
        ),
    ]

    strategy = RoundRobinStrategy()

    selected = []

    index = 0

    while index < 6:
        selected.append(
            strategy.select(
                "service",
                instances,
            ).instance_id
        )

        index += 1

    eq(
        selected,
        [
            "a",
            "b",
            "c",
            "a",
            "b",
            "c",
        ],
        "deterministic round robin",
    )


def test_round_robin_skips_unhealthy():
    a = ServiceInstance(
        "a",
        "service",
        success_handler("a"),
    )

    b = ServiceInstance(
        "b",
        "service",
        success_handler("b"),
    )

    b.mark_unhealthy()

    strategy = RoundRobinStrategy()

    eq(
        strategy.select(
            "service",
            [a, b],
        ).instance_id,
        "a",
        "round robin skips unhealthy instance",
    )


def test_least_load():
    a = ServiceInstance(
        "a",
        "service",
        success_handler("a"),
    )

    b = ServiceInstance(
        "b",
        "service",
        success_handler("b"),
    )

    a.begin_request()
    a.begin_request()
    b.begin_request()

    selected = LeastLoadStrategy().select(
        "service",
        [a, b],
    )

    eq(
        selected.instance_id,
        "b",
        "least-load selection",
    )

    a.finish_success()
    a.finish_success()
    b.finish_success()


def test_adaptive_tie_rotation():
    instances = [
        ServiceInstance(
            "a",
            "service",
            success_handler("a"),
        ),
        ServiceInstance(
            "b",
            "service",
            success_handler("b"),
        ),
    ]

    strategy = AdaptiveStrategy()

    first = strategy.select(
        "service",
        instances,
    )

    second = strategy.select(
        "service",
        instances,
    )

    eq(
        first.instance_id,
        "a",
        "adaptive tie starts first",
    )

    eq(
        second.instance_id,
        "b",
        "adaptive tie rotates",
    )


def test_dispatch_round_robin():
    balancer = LoadBalancer(
        strategy=RoundRobinStrategy(),
        max_attempts=1,
    )

    balancer.register(
        ServiceInstance(
            "rag-1",
            "rag_service",
            success_handler("rag-1"),
        )
    )

    balancer.register(
        ServiceInstance(
            "rag-2",
            "rag_service",
            success_handler("rag-2"),
        )
    )

    results = []

    index = 0

    while index < 4:
        request = ServiceRequest(
            "req-" + str(index),
            "rag_service",
            "answer",
        )

        response = balancer.dispatch(
            request
        )

        results.append(
            response.data[
                "instance"
            ]
        )

        index += 1

    eq(
        results,
        [
            "rag-1",
            "rag-2",
            "rag-1",
            "rag-2",
        ],
        "dispatch distributes round robin",
    )


def test_retry_on_failure():
    calls = {
        "bad": 0,
        "good": 0,
    }

    def bad_handler(request):
        calls["bad"] += 1
        raise RuntimeError(
            "simulated failure"
        )

    def good_handler(request):
        calls["good"] += 1

        return ServiceResponse.success_response(
            request,
            data={
                "instance": "good",
            },
        )

    balancer = LoadBalancer(
        strategy=RoundRobinStrategy(),
        max_attempts=2,
    )

    bad = ServiceInstance(
        "bad",
        "inference_service",
        bad_handler,
        max_consecutive_failures=1,
    )

    good = ServiceInstance(
        "good",
        "inference_service",
        good_handler,
    )

    balancer.register(
        bad
    ).register(
        good
    )

    response = balancer.dispatch(
        ServiceRequest(
            "req",
            "inference_service",
            "generate",
        )
    )

    eq(
        response.success,
        True,
        "retry eventually succeeds",
    )

    eq(
        response.data["instance"],
        "good",
        "retry uses next instance",
    )

    eq(
        response.metadata[
            "load_balancer_attempt"
        ],
        2,
        "retry attempt metadata",
    )

    check(
        not bad.healthy,
        "failing instance marked unhealthy",
    )

    eq(
        calls,
        {
            "bad": 1,
            "good": 1,
        },
        "each attempted handler called once",
    )


def test_all_fail():
    def bad_handler(request):
        raise ValueError(
            "failure"
        )

    balancer = LoadBalancer(
        max_attempts=3,
    )

    balancer.register(
        ServiceInstance(
            "a",
            "training_service",
            bad_handler,
        )
    )

    balancer.register(
        ServiceInstance(
            "b",
            "training_service",
            bad_handler,
        )
    )

    response = balancer.dispatch(
        ServiceRequest(
            "req",
            "training_service",
            "train",
        )
    )

    eq(
        response.success,
        False,
        "all-failure response unsuccessful",
    )

    eq(
        response.error.code,
        "SERVICE_INSTANCE_FAILURE",
        "all-failure error code",
    )

    eq(
        response.metadata[
            "load_balancer_attempts"
        ],
        2,
        "attempts stop when instances exhausted",
    )

    eq(
        len(
            response.error.details[
                "failures"
            ]
        ),
        2,
        "failure details retain each attempt",
    )


def test_unregistered_service():
    balancer = LoadBalancer()

    response = balancer.dispatch(
        ServiceRequest(
            "req",
            "missing_service",
            "run",
        )
    )

    eq(
        response.error.code,
        "SERVICE_UNAVAILABLE",
        "missing service response",
    )

    eq(
        response.error.retryable,
        True,
        "missing service is retryable",
    )


def test_protocol_compatibility():
    balancer = LoadBalancer(
        max_attempts=1,
    )

    balancer.register(
        ServiceInstance(
            "guard-1",
            "guardrail_service",
            success_handler("guard-1"),
        )
    )

    request = ServiceRequest(
        "req-protocol",
        "guardrail_service",
        "inspect",
        payload={
            "text": "hello",
        },
        trace_id="trace-x",
    )

    codec = ProtocolCodec()

    request = codec.decode_request(
        codec.encode_request(
            request
        )
    )

    response = balancer.dispatch(
        request
    )

    restored = codec.decode_response(
        codec.encode_response(
            response
        )
    )

    eq(
        restored.success,
        True,
        "load balancer response survives protocol codec",
    )

    eq(
        restored.trace_id,
        "trace-x",
        "trace ID survives load balancer + protocol",
    )

    eq(
        restored.metadata[
            "load_balancer_instance_id"
        ],
        "guard-1",
        "selected instance metadata survives protocol",
    )


def test_health_snapshot():
    balancer = LoadBalancer()

    balancer.register(
        ServiceInstance(
            "embedding-1",
            "embedding_service",
            success_handler("embedding-1"),
            metadata={
                "zone": "primary",
            },
        )
    )

    snapshot = balancer.health_snapshot()

    eq(
        snapshot[
            "embedding_service"
        ][0]["instance_id"],
        "embedding-1",
        "health snapshot instance",
    )

    eq(
        snapshot[
            "embedding_service"
        ][0]["metadata"]["zone"],
        "primary",
        "health snapshot metadata",
    )


def test_validation():
    expect_error(
        ValueError,
        lambda: ServiceInstance(
            "",
            "service",
            success_handler("x"),
        ),
        "empty instance ID rejected",
    )

    expect_error(
        ValueError,
        lambda: LoadBalancer(
            max_attempts=0
        ),
        "invalid attempts rejected",
    )

    expect_error(
        TypeError,
        lambda: LoadBalancer().dispatch(
            {}
        ),
        "non-ServiceRequest rejected",
    )

    registry = ServiceRegistry()

    instance = ServiceInstance(
        "x",
        "service",
        success_handler("x"),
    )

    registry.register(
        instance
    )

    expect_error(
        ValueError,
        lambda: registry.register(
            ServiceInstance(
                "x",
                "other",
                success_handler("x2"),
            )
        ),
        "duplicate global instance ID rejected",
    )


def main():
    test_instance_lifecycle()
    test_failure_health_threshold()
    test_registry()
    test_round_robin()
    test_round_robin_skips_unhealthy()
    test_least_load()
    test_adaptive_tie_rotation()
    test_dispatch_round_robin()
    test_retry_on_failure()
    test_all_fail()
    test_unregistered_service()
    test_protocol_compatibility()
    test_health_snapshot()
    test_validation()

    print(
        "LOAD BALANCER TEST SUITE: PASS"
    )
    print(
        "Assertions passed:",
        ASSERTIONS,
    )
    print(
        "Files validated: 4/4"
    )
    print(
        "Service registration/health state: VALIDATED"
    )
    print(
        "Round-robin distribution: VALIDATED"
    )
    print(
        "Least-load/adaptive routing: VALIDATED"
    )
    print(
        "Failure retry + unhealthy isolation: VALIDATED"
    )
    print(
        "Protocol request/response compatibility: VALIDATED"
    )
    print(
        "Health/load accounting: VALIDATED"
    )
    print(
        "Third-party dependencies: 0"
    )


main()
