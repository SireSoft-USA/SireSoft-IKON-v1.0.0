PARSER_BASE = "libs/data/parsers/"
PROTOCOL_BASE = "libs/protocol/"
EVENT_BASE = "services/event_bus/"
NOTIFY_BASE = "services/notification_service/"
CONFIG_BASE = "configs/notification/"

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
        ],
    ),
    (
        NOTIFY_BASE,
        [
            "notification.py",
            "template.py",
            "channel.py",
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
    "channel.py",
    "template.py",
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
            "notification config implementation contains forbidden import: "
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


class InAppTransport:
    def __init__(
        self,
    ):
        self.delivered = []

    def deliver(
        self,
        notification,
    ):
        self.delivered.append({
            "recipient": (
                notification.recipient
            ),
            "subject": (
                notification.subject
            ),
            "body": (
                notification.body
            ),
        })

        return {
            "provider_id": (
                "local-"
                + str(
                    len(
                        self.delivered
                    )
                )
            ),
        }


class FlakyTransport:
    def __init__(
        self,
    ):
        self.calls = 0

    def deliver(
        self,
        notification,
    ):
        self.calls += 1

        if self.calls == 1:
            raise RuntimeError(
                "temporary failure"
            )

        return {
            "ok": True,
        }


def sample_config(
    attach_event_bus=False,
):
    return NotificationConfig(
        channels=[
            NotificationChannelConfig(
                "in_app",
                "in_app",
                enabled=True,
                required_handler=True,
                metadata={
                    "kind": "local",
                },
            ),
            NotificationChannelConfig(
                "webhook",
                "webhook",
                enabled=True,
                required_handler=True,
            ),
            NotificationChannelConfig(
                "email",
                "email",
                enabled=False,
                required_handler=False,
            ),
        ],
        templates=[
            NotificationTemplateConfig(
                "welcome",
                body_template=(
                    "Hello {{name}}, welcome to {{product}}."
                ),
                subject_template=(
                    "Welcome {{name}}"
                ),
                enabled=True,
            ),
            NotificationTemplateConfig(
                "disabled-template",
                body_template="unused",
                enabled=False,
            ),
        ],
        attach_event_bus=(
            attach_event_bus
        ),
        metadata={
            "profile": "runtime",
        },
    )


def test_channel_config():
    channel = NotificationChannelConfig(
        "in_app",
        "handler",
    )

    eq(
        channel.handler_key,
        "handler",
        "channel runtime handler key stored",
    )

    expect_error(
        ValueError,
        lambda: (
            NotificationChannelConfig(
                "",
                "handler",
            )
        ),
        "empty channel ID rejected",
    )


def test_template_config():
    template = (
        NotificationTemplateConfig(
            "welcome",
            "Hello {{name}}",
            "Welcome",
        )
    )

    eq(
        template.subject_template,
        "Welcome",
        "template subject stored",
    )

    expect_error(
        TypeError,
        lambda: (
            NotificationTemplateConfig(
                "bad",
                None,
            )
        ),
        "non-string body template rejected",
    )


def test_defaults():
    config = (
        default_notification_config()
    )

    eq(
        len(
            config.channels
        ),
        2,
        "default notification config includes local and optional email channels",
    )

    eq(
        len(
            config.templates
        ),
        2,
        "default notification templates configured",
    )

    eq(
        config.attach_event_bus,
        True,
        "default notification config attaches event bus",
    )


def test_codec():
    text = (
        '{"channels":['
        '{"channel_id":"in_app",'
        '"handler_key":"local",'
        '"enabled":true,'
        '"required_handler":true,'
        '"metadata":{"kind":"local"}}'
        '],'
        '"templates":['
        '{"template_id":"hello",'
        '"body_template":"Hello {{name}}",'
        '"subject_template":"Hi",'
        '"enabled":true}'
        '],'
        '"attach_event_bus":false,'
        '"metadata":{"profile":"prod"}'
        '}'
    )

    config = (
        NotificationConfigCodec()
        .decode_text(
            text
        )
    )

    eq(
        config.channels[
            0
        ].handler_key,
        "local",
        "codec channel handler key",
    )

    eq(
        config.templates[
            0
        ].template_id,
        "hello",
        "codec template ID",
    )

    eq(
        config.metadata[
            "profile"
        ],
        "prod",
        "codec metadata",
    )


def test_validator():
    config = NotificationConfig(
        channels=[
            NotificationChannelConfig(
                "email",
                "email",
                enabled=False,
                required_handler=False,
            ),
        ],
    )

    result = (
        NotificationConfigValidator()
        .validate(
            config
        )
    )

    eq(
        result[
            "valid"
        ],
        False,
        "notification config requires enabled channel",
    )

    eq(
        result[
            "errors"
        ][0][
            "code"
        ],
        "NO_ENABLED_NOTIFICATION_CHANNELS",
        "enabled-channel validation code",
    )


def test_build_manager():
    in_app = InAppTransport()
    webhook = FlakyTransport()

    result = (
        NotificationConfigFactory()
        .build_manager(
            sample_config(),
            handlers={
                "in_app": in_app,
                "webhook": webhook,
            },
        )
    )

    manager = result[
        "manager"
    ]

    eq(
        result[
            "registered_channel_count"
        ],
        2,
        "required configured channels registered",
    )

    eq(
        result[
            "registered_template_count"
        ],
        1,
        "disabled template excluded",
    )

    eq(
        result[
            "skipped_channel_ids"
        ],
        [
            "email",
        ],
        "missing optional transport skipped",
    )

    eq(
        manager.status()[
            "template_count"
        ],
        1,
        "manager receives enabled template",
    )


def test_template_delivery():
    in_app = InAppTransport()

    manager = (
        NotificationConfigFactory()
        .build_manager(
            NotificationConfig(
                channels=[
                    NotificationChannelConfig(
                        "in_app",
                        "in_app",
                    ),
                ],
                templates=[
                    NotificationTemplateConfig(
                        "welcome",
                        (
                            "Hello {{name}}, "
                            "welcome to {{product}}."
                        ),
                        (
                            "Welcome {{name}}"
                        ),
                    ),
                ],
            ),
            handlers={
                "in_app": in_app,
            },
        )[
            "manager"
        ]
    )

    result = manager.send(
        channel_id="in_app",
        recipient="user-1",
        now=100,
        template_id="welcome",
        variables={
            "name": "Anamta",
            "product": "SireLLM",
        },
        trace_id="trace-1",
        correlation_id="corr-1",
    )

    eq(
        result[
            "success"
        ],
        True,
        "configured template delivery succeeds",
    )

    eq(
        in_app.delivered[
            0
        ][
            "body"
        ],
        (
            "Hello Anamta, "
            "welcome to SireLLM."
        ),
        "configured template rendered through real manager",
    )

    eq(
        result[
            "notification"
        ][
            "provider_result"
        ][
            "provider_id"
        ],
        "local-1",
        "provider result retained",
    )

    eq(
        result[
            "notification"
        ][
            "trace_id"
        ],
        "trace-1",
        "notification trace retained",
    )


def test_failure_retry():
    flaky = FlakyTransport()

    manager = (
        NotificationConfigFactory()
        .build_manager(
            NotificationConfig(
                channels=[
                    NotificationChannelConfig(
                        "webhook",
                        "webhook",
                    ),
                ],
            ),
            handlers={
                "webhook": flaky,
            },
        )[
            "manager"
        ]
    )

    first = manager.send(
        "webhook",
        "endpoint-1",
        now=1,
        body="event",
    )

    eq(
        first[
            "success"
        ],
        False,
        "configured transport failure captured",
    )

    retried = manager.retry(
        first[
            "notification"
        ][
            "notification_id"
        ],
        now=2,
    )

    eq(
        retried[
            "success"
        ],
        True,
        "configured notification retries through same runtime handler",
    )

    eq(
        retried[
            "notification"
        ][
            "attempts"
        ],
        2,
        "notification attempts increment across retry",
    )


def test_event_bus():
    bus = EventBusManager(
        max_history=20
    )
    in_app = InAppTransport()

    manager = (
        NotificationConfigFactory()
        .build_manager(
            NotificationConfig(
                channels=[
                    NotificationChannelConfig(
                        "in_app",
                        "in_app",
                    ),
                ],
                attach_event_bus=True,
            ),
            handlers={
                "in_app": in_app,
            },
            event_bus=bus,
        )[
            "manager"
        ]
    )

    manager.send(
        "in_app",
        "u1",
        now=10,
        body="hello",
        trace_id="trace-notify",
    )

    history = bus.history(
        limit=10
    )

    eq(
        [
            event[
                "topic"
            ]
            for event
            in history[
                "events"
            ]
        ],
        [
            "notification.created",
            "notification.delivered",
        ],
        "notification lifecycle publishes to configured event bus",
    )

    eq(
        history[
            "events"
        ][1][
            "trace_id"
        ],
        "trace-notify",
        "notification event preserves trace metadata",
    )


def test_missing_event_bus():
    expect_error(
        ValueError,
        lambda: (
            NotificationConfigFactory()
            .build_manager(
                sample_config(
                    attach_event_bus=True
                ),
                handlers={
                    "in_app": (
                        InAppTransport()
                    ),
                    "webhook": (
                        FlakyTransport()
                    ),
                },
            )
        ),
        "required notification event bus enforced",
    )


def test_missing_required_handler():
    expect_error(
        KeyError,
        lambda: (
            NotificationConfigFactory()
            .build_manager(
                sample_config(),
                handlers={
                    "in_app": (
                        InAppTransport()
                    ),
                },
            )
        ),
        "missing required notification transport rejected",
    )


def test_channel_enable_disable():
    in_app = InAppTransport()

    manager = (
        NotificationConfigFactory()
        .build_manager(
            NotificationConfig(
                channels=[
                    NotificationChannelConfig(
                        "in_app",
                        "in_app",
                        enabled=False,
                        required_handler=True,
                    ),
                    NotificationChannelConfig(
                        "fallback",
                        "fallback",
                        enabled=True,
                        required_handler=True,
                    ),
                ],
            ),
            handlers={
                "in_app": in_app,
                "fallback": (
                    InAppTransport()
                ),
            },
        )[
            "manager"
        ]
    )

    failed = manager.send(
        "in_app",
        "u1",
        now=1,
        body="hello",
    )

    eq(
        failed[
            "success"
        ],
        False,
        "configured disabled channel rejects delivery",
    )

    manager.enable_channel(
        "in_app"
    )

    retried = manager.retry(
        failed[
            "notification"
        ][
            "notification_id"
        ],
        now=2,
    )

    eq(
        retried[
            "success"
        ],
        True,
        "runtime channel enable allows retry",
    )


def test_service_creation():
    in_app = InAppTransport()
    webhook = FlakyTransport()

    service = (
        NotificationConfigFactory()
        .build_service(
            sample_config(),
            handlers={
                "in_app": in_app,
                "webhook": webhook,
            },
        )
    )

    check(
        isinstance(
            service,
            NotificationService,
        ),
        "factory creates NotificationService",
    )

    status = service.handle(
        ServiceRequest(
            "notify-status",
            "notification_service",
            "status",
        )
    )

    eq(
        status.success,
        True,
        "configured notification service responds",
    )

    eq(
        status.data[
            "status"
        ][
            "channel_count"
        ],
        2,
        "configured notification service exposes channel count",
    )

    sent = service.handle(
        ServiceRequest(
            "notify-send",
            "notification_service",
            "send",
            payload={
                "channel_id": (
                    "in_app"
                ),
                "recipient": "u1",
                "now": 5,
                "template_id": (
                    "welcome"
                ),
                "variables": {
                    "name": "User",
                    "product": (
                        "SireLLM"
                    ),
                },
            },
            trace_id="trace-service",
        )
    )

    eq(
        sent.success,
        True,
        "configured notification service sends",
    )

    eq(
        sent.data[
            "delivery"
        ][
            "notification"
        ][
            "trace_id"
        ],
        "trace-service",
        "protocol notification trace propagated",
    )

    eq(
        in_app.delivered[
            0
        ][
            "body"
        ],
        (
            "Hello User, "
            "welcome to SireLLM."
        ),
        "protocol send renders configured template",
    )


def main():
    test_channel_config()
    test_template_config()
    test_defaults()
    test_codec()
    test_validator()
    test_build_manager()
    test_template_delivery()
    test_failure_retry()
    test_event_bus()
    test_missing_event_bus()
    test_missing_required_handler()
    test_channel_enable_disable()
    test_service_creation()

    print(
        "NOTIFICATION CONFIG TEST SUITE: PASS"
    )
    print(
        "Assertions passed:",
        ASSERTIONS,
    )
    print(
        "Files validated: 7/7"
    )
    print(
        "Typed channel/template topology: VALIDATED"
    )
    print(
        "Handwritten JSON decoding: VALIDATED"
    )
    print(
        "Runtime-only transport resolution: VALIDATED"
    )
    print(
        "Template rendering/delivery: VALIDATED"
    )
    print(
        "Failure/retry/channel lifecycle: VALIDATED"
    )
    print(
        "EventBus notification lifecycle integration: VALIDATED"
    )
    print(
        "Trace propagation: VALIDATED"
    )
    print(
        "NotificationService generation: VALIDATED"
    )
    print(
        "Third-party dependencies: 0"
    )


main()
