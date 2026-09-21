SERIAL_BASE = "libs/core/serialization/"
PROTOCOL_BASE = "libs/protocol/"
EVENT_BASE = "services/event_bus/"
SERVICE_BASE = "services/notification_service/"

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
    "notification.py",
    "template.py",
    "channel.py",
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
            "notification_service implementation contains forbidden import: "
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


def test_template_rendering():
    template = NotificationTemplate(
        "welcome",
        subject_template=(
            "Welcome {{name}}"
        ),
        body_template=(
            "Hi {{ name }}, your role is {{role}}."
        ),
    )

    rendered = template.render({
        "name": "Anamta",
        "role": "developer",
    })

    eq(
        rendered[
            "subject"
        ],
        "Welcome Anamta",
        "subject template rendered",
    )

    eq(
        rendered[
            "body"
        ],
        (
            "Hi Anamta, your role is developer."
        ),
        "body template rendered",
    )


def test_template_missing_variable():
    template = NotificationTemplate(
        "x",
        body_template=(
            "Hello {{name}}"
        ),
    )

    expect_error(
        KeyError,
        lambda: template.render(
            {}
        ),
        "missing template variable rejected",
    )


def test_direct_delivery():
    manager = NotificationManager()

    delivered = []

    manager.register_channel(
        "in_app",
        lambda notification: delivered.append(
            (
                notification.recipient,
                notification.body,
            )
        ) or {
            "provider_id": "local-1",
        },
    )

    result = manager.send(
        channel_id="in_app",
        recipient="u1",
        now=100,
        subject="Hello",
        body="Welcome",
    )

    eq(
        result[
            "success"
        ],
        True,
        "direct notification delivery succeeds",
    )

    eq(
        delivered,
        [
            (
                "u1",
                "Welcome",
            ),
        ],
        "channel receives notification",
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


def test_template_delivery():
    manager = NotificationManager()

    captured = []

    manager.register_channel(
        "email",
        lambda notification: captured.append(
            (
                notification.subject,
                notification.body,
            )
        ),
    )

    manager.create_template(
        "reset",
        subject_template=(
            "Reset for {{name}}"
        ),
        body_template=(
            "Code: {{code}}"
        ),
    )

    result = manager.send(
        channel_id="email",
        recipient="user@example.com",
        now=1,
        template_id="reset",
        variables={
            "name": "User",
            "code": 1234,
        },
    )

    eq(
        result[
            "success"
        ],
        True,
        "template-based delivery succeeds",
    )

    eq(
        captured,
        [
            (
                "Reset for User",
                "Code: 1234",
            ),
        ],
        "template content delivered",
    )


def test_failed_delivery_and_retry():
    manager = NotificationManager()

    state = {
        "attempt": 0,
    }

    def flaky(
        notification,
    ):
        state[
            "attempt"
        ] += 1

        if state[
            "attempt"
        ] == 1:
            raise RuntimeError(
                "temporary failure"
            )

        return {
            "ok": True,
        }

    manager.register_channel(
        "webhook",
        flaky,
    )

    first = manager.send(
        "webhook",
        "endpoint-1",
        now=10,
        body="event",
    )

    eq(
        first[
            "success"
        ],
        False,
        "first delivery failure captured",
    )

    notification_id = first[
        "notification"
    ][
        "notification_id"
    ]

    eq(
        first[
            "notification"
        ][
            "status"
        ],
        "failed",
        "failed notification state",
    )

    retried = manager.retry(
        notification_id,
        now=11,
    )

    eq(
        retried[
            "success"
        ],
        True,
        "failed notification can be retried",
    )

    eq(
        retried[
            "notification"
        ][
            "attempts"
        ],
        2,
        "retry increments attempts",
    )


def test_disabled_channel():
    manager = NotificationManager()

    manager.register_channel(
        "email",
        lambda notification: None,
        enabled=False,
    )

    result = manager.send(
        "email",
        "x@example.com",
        now=1,
        body="hello",
    )

    eq(
        result[
            "success"
        ],
        False,
        "disabled channel produces failed delivery",
    )

    manager.enable_channel(
        "email"
    )

    retried = manager.retry(
        result[
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
        "reenabled channel can deliver retry",
    )


def test_cancel():
    manager = NotificationManager()

    manager.register_channel(
        "x",
        lambda notification: (_ for _ in ()).throw(
            RuntimeError(
                "fail"
            )
        ),
    )

    result = manager.send(
        "x",
        "r",
        now=1,
        body="body",
    )

    notification_id = result[
        "notification"
    ][
        "notification_id"
    ]

    cancelled = manager.cancel(
        notification_id,
        now=2,
    )

    eq(
        cancelled.status,
        "cancelled",
        "failed notification can be cancelled",
    )

    expect_error(
        RuntimeError,
        lambda: manager.retry(
            notification_id,
            now=3,
        ),
        "cancelled notification cannot be retried",
    )


def test_list_filters():
    manager = NotificationManager()

    manager.register_channel(
        "a",
        lambda notification: None,
    )

    manager.register_channel(
        "b",
        lambda notification: None,
    )

    manager.send(
        "a",
        "u1",
        now=1,
        body="one",
    )

    manager.send(
        "b",
        "u2",
        now=2,
        body="two",
    )

    filtered = manager.list_notifications(
        channel_id="b",
        recipient="u2",
    )

    eq(
        len(
            filtered
        ),
        1,
        "notification filters narrow history",
    )

    eq(
        filtered[
            0
        ][
            "body"
        ],
        "two",
        "filtered notification correct",
    )


def test_event_bus_integration():
    event_bus = EventBusManager()

    seen = []

    event_bus.subscribe(
        "notification-events",
        "notification.",
        lambda event: seen.append(
            event.topic
        ),
        mode="prefix",
    )

    manager = NotificationManager(
        event_bus=event_bus
    )

    manager.register_channel(
        "in_app",
        lambda notification: None,
    )

    manager.send(
        "in_app",
        "u1",
        now=10,
        body="hello",
        trace_id="trace-notification",
    )

    eq(
        seen,
        [
            "notification.created",
            "notification.delivered",
        ],
        "notification lifecycle events published",
    )

    history = event_bus.history(
        topic=(
            "notification.delivered"
        )
    )

    eq(
        history[
            "events"
        ][0][
            "trace_id"
        ],
        "trace-notification",
        "notification trace propagated to event bus",
    )


def test_status():
    manager = NotificationManager()

    manager.register_channel(
        "success",
        lambda notification: None,
    )

    manager.register_channel(
        "failure",
        lambda notification: (_ for _ in ()).throw(
            RuntimeError(
                "fail"
            )
        ),
    )

    manager.create_template(
        "basic",
        body_template="hello",
    )

    manager.send(
        "success",
        "a",
        now=1,
        body="ok",
    )

    manager.send(
        "failure",
        "b",
        now=2,
        body="bad",
    )

    status = manager.status()

    eq(
        status[
            "channel_count"
        ],
        2,
        "status channel count",
    )

    eq(
        status[
            "template_count"
        ],
        1,
        "status template count",
    )

    eq(
        status[
            "counts"
        ][
            "delivered"
        ],
        1,
        "status delivered count",
    )

    eq(
        status[
            "counts"
        ][
            "failed"
        ],
        1,
        "status failed count",
    )


def test_service_flow():
    manager = NotificationManager()

    delivered = []

    manager.register_channel(
        "in_app",
        lambda notification: delivered.append(
            notification.body
        ),
    )

    service = NotificationService(
        manager
    )

    created = service.handle(
        ServiceRequest(
            "s1",
            "notification_service",
            "create_template",
            payload={
                "template_id": "hello",
                "body_template": (
                    "Hello {{name}}"
                ),
            },
        )
    )

    eq(
        created.success,
        True,
        "service creates template",
    )

    sent = service.handle(
        ServiceRequest(
            "s2",
            "notification_service",
            "send",
            payload={
                "channel_id": "in_app",
                "recipient": "u1",
                "now": 100,
                "template_id": "hello",
                "variables": {
                    "name": "User",
                },
            },
            trace_id="trace-service",
        )
    )

    eq(
        sent.success,
        True,
        "service sends notification",
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
        "service request trace propagated",
    )

    eq(
        delivered,
        [
            "Hello User",
        ],
        "service rendered and delivered template",
    )


def test_protocol_round_trip():
    manager = NotificationManager()

    manager.register_channel(
        "in_app",
        lambda notification: {
            "id": "provider-1",
        },
    )

    service = NotificationService(
        manager
    )

    codec = ProtocolCodec()

    request = ServiceRequest(
        "protocol-notification",
        "notification_service",
        "send",
        payload={
            "channel_id": "in_app",
            "recipient": "u1",
            "now": 5,
            "subject": "Hello",
            "body": "World",
        },
        trace_id="trace-notification",
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
        "notification send survives protocol codec",
    )

    eq(
        response.trace_id,
        "trace-notification",
        "notification service trace preserved",
    )

    eq(
        response.data[
            "delivery"
        ][
            "notification"
        ][
            "provider_result"
        ][
            "id"
        ],
        "provider-1",
        "provider result survives protocol",
    )


def test_errors():
    service = NotificationService(
        NotificationManager()
    )

    missing_channel = service.handle(
        ServiceRequest(
            "e1",
            "notification_service",
            "send",
            payload={
                "channel_id": "missing",
                "recipient": "u1",
                "now": 1,
                "body": "x",
            },
        )
    )

    eq(
        missing_channel.error.code,
        "NOT_FOUND",
        "missing channel maps to NOT_FOUND",
    )

    invalid = service.handle(
        ServiceRequest(
            "e2",
            "notification_service",
            "create_template",
            payload={
                "template_id": "",
                "body_template": "x",
            },
        )
    )

    eq(
        invalid.error.code,
        "INVALID_REQUEST",
        "invalid template maps to INVALID_REQUEST",
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
        "wrong service rejected",
    )

    expect_error(
        TypeError,
        lambda: service.handle(
            {}
        ),
        "non-ServiceRequest rejected",
    )


def test_validation():
    manager = NotificationManager()

    manager.register_channel(
        "x",
        lambda notification: None,
    )

    expect_error(
        ValueError,
        lambda: manager.register_channel(
            "x",
            lambda notification: None,
        ),
        "duplicate channel rejected",
    )

    manager.create_template(
        "t",
        body_template="x",
    )

    expect_error(
        ValueError,
        lambda: manager.create_template(
            "t",
            body_template="y",
        ),
        "duplicate template rejected",
    )

    expect_error(
        ValueError,
        lambda: manager.send(
            "x",
            "",
            now=1,
            body="x",
        ),
        "empty recipient rejected",
    )


def main():
    test_template_rendering()
    test_template_missing_variable()
    test_direct_delivery()
    test_template_delivery()
    test_failed_delivery_and_retry()
    test_disabled_channel()
    test_cancel()
    test_list_filters()
    test_event_bus_integration()
    test_status()
    test_service_flow()
    test_protocol_round_trip()
    test_errors()
    test_validation()

    print(
        "NOTIFICATION SERVICE TEST SUITE: PASS"
    )
    print(
        "Assertions passed:",
        ASSERTIONS,
    )
    print(
        "Files validated: 5/5"
    )
    print(
        "Template rendering/validation: VALIDATED"
    )
    print(
        "Local delivery-channel abstraction: VALIDATED"
    )
    print(
        "Failure/retry/cancellation lifecycle: VALIDATED"
    )
    print(
        "Trace/correlation propagation: VALIDATED"
    )
    print(
        "Notification history/filtering: VALIDATED"
    )
    print(
        "Event-bus lifecycle publication: VALIDATED"
    )
    print(
        "Protocol service operations: VALIDATED"
    )
    print(
        "Third-party dependencies: 0"
    )


main()
