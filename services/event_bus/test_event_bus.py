SERIAL_BASE = "libs/core/serialization/"
PROTOCOL_BASE = "libs/protocol/"
SERVICE_BASE = "services/event_bus/"

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
    "event.py",
    "subscription.py",
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
            "event_bus implementation contains forbidden import: "
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


def test_exact_delivery_order():
    manager = EventBusManager()

    delivered = []

    manager.subscribe(
        "a",
        "model.loaded",
        lambda event: delivered.append(
            "a:"
            + event.event_id
        ),
    )

    manager.subscribe(
        "b",
        "model.loaded",
        lambda event: delivered.append(
            "b:"
            + event.event_id
        ),
    )

    result = manager.publish(
        "model.loaded",
        timestamp=100,
        payload={
            "model_id": "sirellm",
        },
    )

    eq(
        delivered,
        [
            "a:event-1",
            "b:event-1",
        ],
        "subscribers receive event in registration order",
    )

    eq(
        result[
            "successful_deliveries"
        ],
        2,
        "successful delivery count",
    )


def test_prefix_subscription():
    manager = EventBusManager()

    seen = []

    manager.subscribe(
        "prefix",
        "training.",
        lambda event: seen.append(
            event.topic
        ),
        mode="prefix",
    )

    manager.publish(
        "training.started",
        timestamp=1,
    )

    manager.publish(
        "training.completed",
        timestamp=2,
    )

    manager.publish(
        "model.loaded",
        timestamp=3,
    )

    eq(
        seen,
        [
            "training.started",
            "training.completed",
        ],
        "prefix subscription matches topic namespace",
    )


def test_disabled_subscription():
    manager = EventBusManager()
    seen = []

    manager.subscribe(
        "x",
        "a",
        lambda event: seen.append(
            event.event_id
        ),
        enabled=False,
    )

    manager.publish(
        "a",
        timestamp=1,
    )

    eq(
        seen,
        [],
        "disabled subscription receives nothing",
    )

    manager.enable_subscription(
        "x"
    )

    manager.publish(
        "a",
        timestamp=2,
    )

    eq(
        seen,
        [
            "event-2",
        ],
        "enabled subscription receives later event",
    )


def test_failure_isolation():
    manager = EventBusManager()

    seen = []

    def failing(
        event,
    ):
        raise RuntimeError(
            "boom"
        )

    manager.subscribe(
        "fail",
        "x",
        failing,
    )

    manager.subscribe(
        "ok",
        "x",
        lambda event: seen.append(
            event.event_id
        ),
    )

    result = manager.publish(
        "x",
        timestamp=1,
    )

    eq(
        result[
            "failed_deliveries"
        ],
        1,
        "failing subscriber counted",
    )

    eq(
        result[
            "successful_deliveries"
        ],
        1,
        "later subscriber still receives event",
    )

    eq(
        seen,
        [
            "event-1",
        ],
        "delivery continues after subscriber failure",
    )


def test_trace_and_correlation():
    manager = EventBusManager()

    result = manager.publish(
        "rag.completed",
        timestamp=10,
        trace_id="trace-1",
        correlation_id="req-9",
        source_service="rag_service",
    )

    event = result[
        "event"
    ]

    eq(
        event[
            "trace_id"
        ],
        "trace-1",
        "event trace preserved",
    )

    eq(
        event[
            "correlation_id"
        ],
        "req-9",
        "event correlation preserved",
    )

    eq(
        event[
            "source_service"
        ],
        "rag_service",
        "event source service preserved",
    )


def test_payload_copy_isolation():
    manager = EventBusManager()

    payload = {
        "items": [
            1,
            2,
        ],
    }

    result = manager.publish(
        "x",
        timestamp=1,
        payload=payload,
    )

    payload[
        "items"
    ].append(
        3
    )

    eq(
        result[
            "event"
        ][
            "payload"
        ],
        {
            "items": [
                1,
                2,
            ],
        },
        "event payload copied at publish time",
    )


def test_history_filtering():
    manager = EventBusManager()

    manager.publish(
        "a",
        1,
    )
    manager.publish(
        "b",
        2,
    )
    manager.publish(
        "a",
        3,
    )

    history = manager.history(
        topic="a",
        minimum_sequence=2,
        limit=10,
    )

    eq(
        [
            event[
                "sequence"
            ]
            for event
            in history[
                "events"
            ]
        ],
        [
            3,
        ],
        "history topic/sequence filters",
    )

    newest = manager.history(
        limit=2,
        newest_first=True,
    )

    eq(
        [
            event[
                "sequence"
            ]
            for event
            in newest[
                "events"
            ]
        ],
        [
            3,
            2,
        ],
        "newest-first history",
    )


def test_bounded_history():
    manager = EventBusManager(
        max_history=2
    )

    manager.publish(
        "a",
        1,
    )
    manager.publish(
        "b",
        2,
    )
    manager.publish(
        "c",
        3,
    )

    eq(
        [
            event[
                "sequence"
            ]
            for event
            in manager.history(
                limit=10
            )[
                "events"
            ]
        ],
        [
            2,
            3,
        ],
        "oldest event evicted from bounded history",
    )

    eq(
        manager.status()[
            "history_evictions"
        ],
        1,
        "history eviction counted",
    )


def test_subscription_stats():
    manager = EventBusManager()

    def fail(
        event,
    ):
        raise ValueError(
            "bad"
        )

    manager.subscribe(
        "ok",
        "x",
        lambda event: "done",
    )

    manager.subscribe(
        "fail",
        "x",
        fail,
    )

    manager.publish(
        "x",
        1,
    )

    ok = manager.get_subscription(
        "ok"
    )

    bad = manager.get_subscription(
        "fail"
    )

    eq(
        ok.delivered,
        1,
        "successful subscriber count",
    )

    eq(
        bad.failed,
        1,
        "failed subscriber count",
    )


def test_unsubscribe():
    manager = EventBusManager()

    manager.subscribe(
        "x",
        "topic",
        lambda event: None,
    )

    removed = manager.unsubscribe(
        "x"
    )

    eq(
        removed.subscription_id,
        "x",
        "unsubscribe returns subscription",
    )

    eq(
        manager.list_subscriptions(),
        [],
        "subscription removed",
    )


def test_clear_history():
    manager = EventBusManager()

    manager.publish(
        "a",
        1,
    )
    manager.publish(
        "b",
        2,
    )

    cleared = manager.clear_history()

    eq(
        cleared[
            "cleared_events"
        ],
        2,
        "clear history reports count",
    )

    eq(
        manager.history()[
            "count"
        ],
        0,
        "history empty after clear",
    )


def test_status():
    manager = EventBusManager()

    manager.subscribe(
        "on",
        "a",
        lambda event: None,
    )

    manager.subscribe(
        "off",
        "b",
        lambda event: None,
        enabled=False,
    )

    manager.publish(
        "a",
        1,
    )

    status = manager.status()

    eq(
        status[
            "subscription_count"
        ],
        2,
        "status subscription count",
    )

    eq(
        status[
            "enabled_subscriptions"
        ],
        1,
        "status enabled count",
    )

    eq(
        status[
            "disabled_subscriptions"
        ],
        1,
        "status disabled count",
    )

    eq(
        status[
            "total_published"
        ],
        1,
        "status published count",
    )

    eq(
        status[
            "total_deliveries"
        ],
        1,
        "status delivery count",
    )


def test_service_publish():
    manager = EventBusManager()

    captured = []

    manager.subscribe(
        "listener",
        "model.promoted",
        lambda event: captured.append(
            event.payload[
                "version"
            ]
        ),
    )

    service = EventBusService(
        manager
    )

    response = service.handle(
        ServiceRequest(
            "p1",
            "event_bus",
            "publish",
            payload={
                "topic": (
                    "model.promoted"
                ),
                "timestamp": 100,
                "payload": {
                    "version": "v2",
                },
                "source_service": (
                    "model_registry"
                ),
            },
            trace_id="trace-bus",
            correlation_id="corr-bus",
        )
    )

    eq(
        response.success,
        True,
        "event bus service publish succeeds",
    )

    eq(
        captured,
        [
            "v2",
        ],
        "service publish reaches runtime subscriber",
    )

    eq(
        response.data[
            "publish"
        ][
            "event"
        ][
            "trace_id"
        ],
        "trace-bus",
        "service request trace propagated to event",
    )


def test_service_controls():
    manager = EventBusManager()

    manager.subscribe(
        "sub",
        "a",
        lambda event: None,
    )

    service = EventBusService(
        manager
    )

    disabled = service.handle(
        ServiceRequest(
            "d",
            "event_bus",
            "disable_subscription",
            payload={
                "subscription_id": "sub",
            },
        )
    )

    eq(
        disabled.data[
            "subscription"
        ][
            "enabled"
        ],
        False,
        "service disables subscription",
    )

    enabled = service.handle(
        ServiceRequest(
            "e",
            "event_bus",
            "enable_subscription",
            payload={
                "subscription_id": "sub",
            },
        )
    )

    eq(
        enabled.data[
            "subscription"
        ][
            "enabled"
        ],
        True,
        "service enables subscription",
    )


def test_protocol_round_trip():
    manager = EventBusManager()

    service = EventBusService(
        manager
    )

    codec = ProtocolCodec()

    request = ServiceRequest(
        "protocol-event",
        "event_bus",
        "publish",
        payload={
            "topic": "training.completed",
            "timestamp": 55,
            "payload": {
                "job_id": "job-1",
                "loss": 0.5,
            },
        },
        trace_id="trace-event",
    )

    request = codec.decode_request(
        codec.encode_request(
            request
        )
    )

    response = service.handle(
        request
    )

    response = codec.decode_response(
        codec.encode_response(
            response
        )
    )

    eq(
        response.success,
        True,
        "event publish survives protocol codec",
    )

    eq(
        response.trace_id,
        "trace-event",
        "event service trace preserved",
    )

    eq(
        response.data[
            "publish"
        ][
            "event"
        ][
            "payload"
        ][
            "job_id"
        ],
        "job-1",
        "event payload survives protocol",
    )


def test_errors():
    service = EventBusService()

    missing = service.handle(
        ServiceRequest(
            "m",
            "event_bus",
            "enable_subscription",
            payload={
                "subscription_id": "missing",
            },
        )
    )

    eq(
        missing.error.code,
        "NOT_FOUND",
        "missing subscription maps to NOT_FOUND",
    )

    invalid = service.handle(
        ServiceRequest(
            "i",
            "event_bus",
            "publish",
            payload={
                "topic": "",
                "timestamp": 1,
            },
        )
    )

    eq(
        invalid.error.code,
        "INVALID_REQUEST",
        "invalid event maps to INVALID_REQUEST",
    )

    wrong = service.handle(
        ServiceRequest(
            "w",
            "rag_service",
            "status",
        )
    )

    eq(
        wrong.error.code,
        "INVALID_REQUEST",
        "wrong target rejected",
    )

    expect_error(
        TypeError,
        lambda: service.handle(
            {}
        ),
        "non-ServiceRequest rejected",
    )


def test_validation():
    manager = EventBusManager()

    manager.subscribe(
        "x",
        "topic",
        lambda event: None,
    )

    expect_error(
        ValueError,
        lambda: manager.subscribe(
            "x",
            "topic",
            lambda event: None,
        ),
        "duplicate subscription rejected",
    )

    expect_error(
        ValueError,
        lambda: manager.history(
            limit=0
        ),
        "invalid history limit rejected",
    )

    expect_error(
        ValueError,
        lambda: EventBusManager(
            max_history=0
        ),
        "invalid history capacity rejected",
    )


def main():
    test_exact_delivery_order()
    test_prefix_subscription()
    test_disabled_subscription()
    test_failure_isolation()
    test_trace_and_correlation()
    test_payload_copy_isolation()
    test_history_filtering()
    test_bounded_history()
    test_subscription_stats()
    test_unsubscribe()
    test_clear_history()
    test_status()
    test_service_publish()
    test_service_controls()
    test_protocol_round_trip()
    test_errors()
    test_validation()

    print(
        "EVENT BUS TEST SUITE: PASS"
    )
    print(
        "Assertions passed:",
        ASSERTIONS,
    )
    print(
        "Files validated: 4/4"
    )
    print(
        "Ordered exact/prefix pub-sub: VALIDATED"
    )
    print(
        "Subscriber failure isolation: VALIDATED"
    )
    print(
        "Trace/correlation propagation: VALIDATED"
    )
    print(
        "Bounded event history/filtering: VALIDATED"
    )
    print(
        "Subscription lifecycle/stats: VALIDATED"
    )
    print(
        "Protocol service operations: VALIDATED"
    )
    print(
        "Third-party dependencies: 0"
    )


main()
