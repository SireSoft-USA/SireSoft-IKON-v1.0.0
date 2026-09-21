PARSER_BASE = "libs/data/parsers/"
PROTOCOL_BASE = "libs/protocol/"
EVENT_BASE = "services/event_bus/"
CONFIG_BASE = "configs/event_bus/"

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
        EVENT_BASE,
        [
            "event.py",
            "subscription.py",
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
    "subscription.py",
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
            "event bus config implementation contains forbidden import: "
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


class Collector:
    def __init__(
        self,
        name,
    ):
        self.name = name
        self.events = []

    def handle_event(
        self,
        event,
    ):
        self.events.append(
            (
                event.sequence,
                event.topic,
                event.payload,
            )
        )

        return {
            "collector": (
                self.name
            ),
            "sequence": (
                event.sequence
            ),
        }


class FailingCollector:
    def handle_event(
        self,
        event,
    ):
        raise RuntimeError(
            "simulated subscriber failure"
        )


def sample_config():
    return EventBusConfig(
        max_history=3,
        subscriptions=[
            EventSubscriptionConfig(
                subscription_id=(
                    "training-prefix"
                ),
                topic="training.",
                handler_key=(
                    "training"
                ),
                mode="prefix",
                enabled=True,
                metadata={
                    "consumer": (
                        "training-observer"
                    ),
                },
            ),
            EventSubscriptionConfig(
                subscription_id=(
                    "model-loaded"
                ),
                topic="model.loaded",
                handler_key="model",
                mode="exact",
                enabled=True,
            ),
            EventSubscriptionConfig(
                subscription_id=(
                    "optional-audit"
                ),
                topic="audit.",
                handler_key="audit",
                mode="prefix",
                enabled=False,
                required_handler=False,
            ),
        ],
        metadata={
            "profile": "runtime",
        },
    )


def test_subscription_config():
    item = EventSubscriptionConfig(
        "x",
        "training.",
        "handler",
        mode="prefix",
    )

    eq(
        item.mode,
        "prefix",
        "subscription mode stored",
    )

    expect_error(
        ValueError,
        lambda: (
            EventSubscriptionConfig(
                "x",
                "topic",
                "handler",
                mode="bad",
            )
        ),
        "invalid subscription mode rejected",
    )


def test_defaults():
    config = (
        default_event_bus_config()
    )

    eq(
        config.max_history,
        10000,
        "default event history capacity",
    )

    eq(
        len(
            config.subscriptions
        ),
        3,
        "default event config includes three optional integration subscriptions",
    )

    eq(
        len(
            config.enabled_subscriptions()
        ),
        0,
        "optional default subscriptions begin disabled",
    )


def test_codec():
    text = (
        '{"max_history":50,'
        '"subscriptions":['
        '{"subscription_id":"train",'
        '"topic":"training.",'
        '"handler_key":"trainer",'
        '"mode":"prefix",'
        '"enabled":true,'
        '"required_handler":true,'
        '"metadata":{"kind":"observer"}}'
        '],'
        '"metadata":{"profile":"prod"}'
        '}'
    )

    config = (
        EventBusConfigCodec()
        .decode_text(
            text
        )
    )

    eq(
        config.max_history,
        50,
        "codec history capacity",
    )

    eq(
        config.subscriptions[
            0
        ].handler_key,
        "trainer",
        "codec runtime handler key",
    )

    eq(
        config.metadata[
            "profile"
        ],
        "prod",
        "codec metadata",
    )


def test_validator():
    config = EventBusConfig(
        max_history=2,
        subscriptions=[
            EventSubscriptionConfig(
                "one",
                "training.",
                "same",
                mode="prefix",
            ),
            EventSubscriptionConfig(
                "two",
                "training.",
                "same",
                mode="prefix",
            ),
        ],
    )

    result = (
        EventBusConfigValidator()
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
        "VERY_SMALL_EVENT_HISTORY"
        in codes,
        "small event history warned",
    )

    check(
        "DUPLICATE_EVENT_DELIVERY_PATH"
        in codes,
        "duplicate event delivery path warned",
    )


def test_build_manager():
    training = Collector(
        "training"
    )
    model = Collector(
        "model"
    )

    result = (
        EventBusConfigFactory()
        .build_manager(
            sample_config(),
            handlers={
                "training": (
                    training
                ),
                "model": model,
            },
        )
    )

    manager = result[
        "manager"
    ]

    eq(
        result[
            "registered_count"
        ],
        2,
        "configured required subscriptions registered",
    )

    eq(
        result[
            "skipped_subscription_ids"
        ],
        [
            "optional-audit",
        ],
        "missing optional handler skipped",
    )

    eq(
        manager.status()[
            "max_history"
        ],
        3,
        "configured bounded history applied",
    )


def test_exact_and_prefix_delivery():
    training = Collector(
        "training"
    )
    model = Collector(
        "model"
    )

    manager = (
        EventBusConfigFactory()
        .build_manager(
            sample_config(),
            handlers={
                "training": training,
                "model": model,
            },
        )[
            "manager"
        ]
    )

    manager.publish(
        "training.started",
        timestamp=1,
        payload={
            "job_id": "job-1",
        },
    )

    manager.publish(
        "training.completed",
        timestamp=2,
        payload={
            "job_id": "job-1",
        },
    )

    manager.publish(
        "model.loaded",
        timestamp=3,
        payload={
            "model_id": "sirellm",
        },
    )

    eq(
        [
            item[
                1
            ]
            for item
            in training.events
        ],
        [
            "training.started",
            "training.completed",
        ],
        "prefix subscription receives training namespace",
    )

    eq(
        [
            item[
                1
            ]
            for item
            in model.events
        ],
        [
            "model.loaded",
        ],
        "exact subscription receives exact topic only",
    )


def test_order_and_failure_isolation():
    order = []

    def first(
        event,
    ):
        order.append(
            "first"
        )

    def fail(
        event,
    ):
        order.append(
            "fail"
        )
        raise RuntimeError(
            "boom"
        )

    def last(
        event,
    ):
        order.append(
            "last"
        )

    config = EventBusConfig(
        subscriptions=[
            EventSubscriptionConfig(
                "first",
                "x",
                "first",
            ),
            EventSubscriptionConfig(
                "fail",
                "x",
                "fail",
            ),
            EventSubscriptionConfig(
                "last",
                "x",
                "last",
            ),
        ],
    )

    manager = (
        EventBusConfigFactory()
        .build_manager(
            config,
            handlers={
                "first": first,
                "fail": fail,
                "last": last,
            },
        )[
            "manager"
        ]
    )

    result = manager.publish(
        "x",
        timestamp=1,
    )

    eq(
        order,
        [
            "first",
            "fail",
            "last",
        ],
        "configured subscribers preserve registration order",
    )

    eq(
        result[
            "failed_deliveries"
        ],
        1,
        "subscriber failure isolated and counted",
    )

    eq(
        result[
            "successful_deliveries"
        ],
        2,
        "later subscribers still receive event after failure",
    )


def test_bounded_history():
    manager = (
        EventBusConfigFactory()
        .build_manager(
            EventBusConfig(
                max_history=2,
                subscriptions=[],
            ),
            handlers={},
        )[
            "manager"
        ]
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

    history = manager.history(
        limit=10
    )

    eq(
        [
            item[
                "sequence"
            ]
            for item
            in history[
                "events"
            ]
        ],
        [
            2,
            3,
        ],
        "configured history evicts oldest event",
    )

    eq(
        manager.status()[
            "history_evictions"
        ],
        1,
        "history eviction metric updated",
    )


def test_missing_required_handler():
    expect_error(
        KeyError,
        lambda: (
            EventBusConfigFactory()
            .build_manager(
                sample_config(),
                handlers={},
            )
        ),
        "missing required event handler rejected",
    )


def test_disabled_subscription_registered():
    audit = Collector(
        "audit"
    )

    config = EventBusConfig(
        subscriptions=[
            EventSubscriptionConfig(
                "audit",
                "audit.",
                "audit",
                mode="prefix",
                enabled=False,
                required_handler=True,
            ),
        ],
    )

    manager = (
        EventBusConfigFactory()
        .build_manager(
            config,
            handlers={
                "audit": audit,
            },
        )[
            "manager"
        ]
    )

    manager.publish(
        "audit.created",
        1,
    )

    eq(
        audit.events,
        [],
        "configured disabled subscription receives nothing",
    )

    manager.enable_subscription(
        "audit"
    )

    manager.publish(
        "audit.created",
        2,
    )

    eq(
        len(
            audit.events
        ),
        1,
        "configured subscription can be enabled at runtime",
    )


def test_service_creation():
    training = Collector(
        "training"
    )
    model = Collector(
        "model"
    )

    service = (
        EventBusConfigFactory()
        .build_service(
            sample_config(),
            handlers={
                "training": training,
                "model": model,
            },
        )
    )

    check(
        isinstance(
            service,
            EventBusService,
        ),
        "factory creates EventBusService",
    )

    publish = service.handle(
        ServiceRequest(
            "event-publish",
            "event_bus",
            "publish",
            payload={
                "topic": (
                    "training.started"
                ),
                "timestamp": 100,
                "payload": {
                    "job_id": "job-9",
                },
                "source_service": (
                    "training_service"
                ),
                "trace_id": (
                    "trace-1"
                ),
            },
        )
    )

    eq(
        publish.success,
        True,
        "configured event bus service publishes",
    )

    eq(
        publish.data[
            "publish"
        ][
            "successful_deliveries"
        ],
        1,
        "configured event bus delivers protocol-published event",
    )

    history = service.handle(
        ServiceRequest(
            "event-history",
            "event_bus",
            "history",
            payload={
                "topic": (
                    "training.started"
                ),
                "limit": 10,
            },
        )
    )

    eq(
        history.data[
            "history"
        ][
            "count"
        ],
        1,
        "configured event bus service exposes history",
    )

    eq(
        history.data[
            "history"
        ][
            "events"
        ][0][
            "trace_id"
        ],
        "trace-1",
        "event trace metadata preserved through service",
    )


def main():
    test_subscription_config()
    test_defaults()
    test_codec()
    test_validator()
    test_build_manager()
    test_exact_and_prefix_delivery()
    test_order_and_failure_isolation()
    test_bounded_history()
    test_missing_required_handler()
    test_disabled_subscription_registered()
    test_service_creation()

    print(
        "EVENT BUS CONFIG TEST SUITE: PASS"
    )
    print(
        "Assertions passed:",
        ASSERTIONS,
    )
    print(
        "Files validated: 6/6"
    )
    print(
        "Typed event subscription topology: VALIDATED"
    )
    print(
        "Handwritten JSON decoding: VALIDATED"
    )
    print(
        "Runtime-only handler resolution: VALIDATED"
    )
    print(
        "Exact/prefix topic matching: VALIDATED"
    )
    print(
        "Ordered delivery/failure isolation: VALIDATED"
    )
    print(
        "Bounded event history/eviction: VALIDATED"
    )
    print(
        "Protocol publish/history integration: VALIDATED"
    )
    print(
        "EventBusService generation: VALIDATED"
    )
    print(
        "Third-party dependencies: 0"
    )


main()
