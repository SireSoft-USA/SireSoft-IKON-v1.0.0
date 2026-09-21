import os

SERIAL_BASE = "libs/core/serialization/"
PARSER_BASE = "libs/data/parsers/"
PROTOCOL_BASE = "libs/protocol/"
EVENT_BASE = "services/event_bus/"
QUEUE_BASE = "services/job_queue/"
SCHED_BASE = "services/scheduler_service/"
CONFIG_BASE = "configs/scheduler/"

namespace = {
    "__builtins__": __builtins__,
}

groups = [
    (SERIAL_BASE, [
        "binary_writer.py",
        "binary_reader.py",
        "checksum.py",
    ]),
    (PARSER_BASE, [
        "json_parser.py",
    ]),
    (PROTOCOL_BASE, [
        "error.py",
        "message.py",
        "request.py",
        "response.py",
    ]),
    (EVENT_BASE, [
        "event.py",
        "subscription.py",
        "manager.py",
    ]),
    (QUEUE_BASE, [
        "job.py",
        "queue.py",
        "persistence.py",
        "manager.py",
    ]),
    (SCHED_BASE, [
        "recurrence.py",
        "schedule.py",
        "persistence.py",
        "manager.py",
        "service.py",
    ]),
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
    "recurrence.py",
    "task.py",
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
            "scheduler config implementation contains forbidden import: "
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
STATE_PATH = (
    "configs/scheduler/"
    "_test_scheduler.sllmsch"
)


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


def cleanup():
    if os.path.isfile(STATE_PATH):
        os.remove(STATE_PATH)


def job_queue():
    manager = JobQueueManager()

    manager.create_queue(
        "training",
        default_lease_seconds=30,
        default_max_attempts=2,
    )

    manager.create_queue(
        "maintenance",
        default_lease_seconds=30,
        default_max_attempts=3,
    )

    return manager


def sample_config(
    attach_event_bus=False,
):
    return SchedulerConfig(
        tasks=[
            ScheduledTaskConfig(
                task_id="one-shot",
                queue_name="training",
                payload={
                    "job": "train",
                },
                next_run_at=10,
                recurrence=SchedulerRecurrenceConfig(
                    mode="once"
                ),
                priority=5,
                max_attempts=2,
                metadata={
                    "kind": "training",
                },
            ),
            ScheduledTaskConfig(
                task_id="repeat",
                queue_name="maintenance",
                payload={
                    "job": "cleanup",
                },
                next_run_at=5,
                recurrence=SchedulerRecurrenceConfig(
                    mode="interval",
                    interval_seconds=10,
                    max_runs=3,
                    catch_up=False,
                ),
                priority=1,
            ),
            ScheduledTaskConfig(
                task_id="disabled",
                queue_name="maintenance",
                payload={
                    "job": "disabled",
                },
                next_run_at=1,
                enabled=False,
            ),
        ],
        attach_event_bus=attach_event_bus,
    )


def test_recurrence_config():
    config = SchedulerRecurrenceConfig(
        mode="interval",
        interval_seconds=30,
        max_runs=4,
    )

    rule = config.to_rule()

    eq(
        rule.interval_seconds,
        30,
        "recurrence interval maps to runtime rule",
    )

    eq(
        rule.max_runs,
        4,
        "recurrence max-runs maps to runtime rule",
    )

    expect_error(
        ValueError,
        lambda: SchedulerRecurrenceConfig(
            mode="interval"
        ),
        "interval recurrence requires interval_seconds",
    )


def test_task_config():
    config = ScheduledTaskConfig(
        "x",
        "training",
        {"value": 1},
        100,
        priority=3,
    )

    eq(
        config.priority,
        3,
        "scheduled task priority stored",
    )

    expect_error(
        ValueError,
        lambda: ScheduledTaskConfig(
            "",
            "training",
            {},
            1,
        ),
        "empty scheduler task ID rejected",
    )


def test_defaults():
    config = default_scheduler_config()

    eq(
        len(config.tasks),
        1,
        "default scheduler contains maintenance template",
    )

    eq(
        config.tasks[0].enabled,
        False,
        "default maintenance schedule is opt-in",
    )

    eq(
        config.attach_event_bus,
        True,
        "default scheduler attaches event bus",
    )


def test_codec():
    text = (
        '{"tasks":['
        '{"task_id":"train-nightly",'
        '"queue_name":"training",'
        '"payload":{"job":"train"},'
        '"next_run_at":100,'
        '"recurrence":{'
        '"mode":"interval",'
        '"interval_seconds":60,'
        '"max_runs":5,'
        '"catch_up":true'
        '},'
        '"priority":4,'
        '"max_attempts":2}'
        '],'
        '"attach_event_bus":false,'
        '"metadata":{"profile":"prod"}'
        '}'
    )

    config = (
        SchedulerConfigCodec()
        .decode_text(text)
    )

    eq(
        config.tasks[0]
        .recurrence.interval_seconds,
        60,
        "codec recurrence interval",
    )

    eq(
        config.tasks[0].priority,
        4,
        "codec scheduler priority",
    )

    eq(
        config.metadata["profile"],
        "prod",
        "codec metadata",
    )


def test_validator():
    queue = job_queue()

    invalid = SchedulerConfig(
        tasks=[
            ScheduledTaskConfig(
                "bad",
                "missing",
                {},
                1,
            ),
        ],
    )

    result = (
        SchedulerConfigValidator()
        .validate(
            invalid,
            job_queue=queue,
        )
    )

    eq(
        result["valid"],
        False,
        "scheduler rejects unavailable queue",
    )

    eq(
        result["errors"][0]["code"],
        "SCHEDULER_QUEUE_UNAVAILABLE",
        "unavailable queue validation code",
    )


def test_manager_generation():
    queue = job_queue()

    manager = (
        SchedulerConfigFactory()
        .build_manager(
            sample_config(),
            queue,
        )
    )

    eq(
        manager.status()[
            "task_count"
        ],
        3,
        "configured scheduler creates all tasks",
    )

    eq(
        manager.status()[
            "counts"
        ][
            "disabled"
        ],
        1,
        "configured disabled task preserved",
    )


def test_due_dispatch_order():
    queue = job_queue()

    manager = (
        SchedulerConfigFactory()
        .build_manager(
            sample_config(),
            queue,
        )
    )

    result = manager.tick(
        now=10,
        trace_id="trace-1",
        correlation_id="corr-1",
    )

    eq(
        result["dispatch_count"],
        2,
        "two due configured tasks dispatch",
    )

    eq(
        [
            item["task_id"]
            for item
            in result["dispatched"]
        ],
        [
            "repeat",
            "one-shot",
        ],
        "due scheduler tasks dispatch by scheduled time then sequence",
    )

    eq(
        manager.get_task(
            "one-shot"
        ).status,
        "completed",
        "one-shot schedule completes after dispatch",
    )

    eq(
        manager.get_task(
            "repeat"
        ).next_run_at,
        20,
        "non-catch-up interval schedules from actual dispatch time",
    )

    training_job = queue.get_job(
        "training",
        result["dispatched"][1][
            "job_id"
        ],
    )

    eq(
        training_job.priority,
        5,
        "scheduler transfers configured priority into job queue",
    )

    eq(
        training_job.metadata[
            "scheduler_task_id"
        ],
        "one-shot",
        "scheduler provenance attached to queued job",
    )

    eq(
        training_job.metadata[
            "scheduler_run_number"
        ],
        1,
        "scheduler run number attached to queued job",
    )


def test_interval_completion():
    queue = job_queue()

    config = SchedulerConfig(
        tasks=[
            ScheduledTaskConfig(
                "repeat",
                "maintenance",
                {"task": "cleanup"},
                5,
                recurrence=SchedulerRecurrenceConfig(
                    mode="interval",
                    interval_seconds=5,
                    max_runs=3,
                ),
            ),
        ],
    )

    manager = (
        SchedulerConfigFactory()
        .build_manager(
            config,
            queue,
        )
    )

    manager.tick(5)
    manager.tick(10)
    manager.tick(15)

    task = manager.get_task(
        "repeat"
    )

    eq(
        task.run_count,
        3,
        "configured interval task stops at max_runs",
    )

    eq(
        task.status,
        "completed",
        "max_runs completes interval task",
    )

    eq(
        task.next_run_at,
        None,
        "completed interval has no next run",
    )


def test_catch_up_behavior():
    queue = job_queue()

    config = SchedulerConfig(
        tasks=[
            ScheduledTaskConfig(
                "cadence",
                "maintenance",
                {},
                10,
                recurrence=SchedulerRecurrenceConfig(
                    mode="interval",
                    interval_seconds=10,
                    max_runs=3,
                    catch_up=True,
                ),
            ),
        ],
    )

    manager = (
        SchedulerConfigFactory()
        .build_manager(
            config,
            queue,
        )
    )

    manager.tick(35)

    eq(
        manager.get_task(
            "cadence"
        ).next_run_at,
        20,
        "catch-up recurrence preserves original cadence",
    )

    result = manager.tick(35)

    eq(
        result["dispatch_count"],
        1,
        "one tick dispatches a due catch-up task at most once",
    )

    eq(
        manager.get_task(
            "cadence"
        ).next_run_at,
        30,
        "second tick advances one cadence step",
    )


def test_event_bus_integration():
    queue = job_queue()
    bus = EventBusManager(
        max_history=20
    )

    manager = (
        SchedulerConfigFactory()
        .build_manager(
            sample_config(
                attach_event_bus=True
            ),
            queue,
            event_bus=bus,
        )
    )

    manager.tick(
        10,
        trace_id="trace-e",
    )

    history = bus.history(
        limit=10
    )

    topics = [
        event["topic"]
        for event
        in history["events"]
    ]

    eq(
        topics,
        [
            "scheduler.dispatched",
            "scheduler.dispatched",
        ],
        "scheduler publishes dispatch lifecycle events",
    )

    eq(
        history[
            "events"
        ][0][
            "trace_id"
        ],
        "trace-e",
        "scheduler event preserves trace metadata",
    )


def test_persistence_round_trip():
    cleanup()
    queue = job_queue()

    manager = (
        SchedulerConfigFactory()
        .build_manager(
            sample_config(),
            queue,
        )
    )

    manager.tick(10)

    artifact = manager.save_state(
        STATE_PATH
    )

    check(
        artifact["bytes"] > 0,
        "scheduler snapshot persisted",
    )

    load_config = SchedulerConfig(
        tasks=[],
        state_path=STATE_PATH,
        load_state_on_start=True,
    )

    loaded = (
        SchedulerConfigFactory()
        .build_manager(
            load_config,
            queue,
        )
    )

    eq(
        loaded.export_state(),
        manager.export_state(),
        "configured scheduler state load reproduces exact state",
    )


def test_missing_event_bus():
    expect_error(
        ValueError,
        lambda: (
            SchedulerConfigFactory()
            .build_manager(
                sample_config(
                    attach_event_bus=True
                ),
                job_queue(),
            )
        ),
        "required scheduler event bus enforced",
    )


def test_service_creation():
    queue = job_queue()

    service = (
        SchedulerConfigFactory()
        .build_service(
            sample_config(),
            queue,
        )
    )

    check(
        isinstance(
            service,
            SchedulerService,
        ),
        "factory creates SchedulerService",
    )

    status = service.handle(
        ServiceRequest(
            "sched-status",
            "scheduler_service",
            "status",
        )
    )

    eq(
        status.success,
        True,
        "configured scheduler service responds",
    )

    eq(
        status.data["status"][
            "task_count"
        ],
        3,
        "configured scheduler service exposes task count",
    )

    tick = service.handle(
        ServiceRequest(
            "sched-tick",
            "scheduler_service",
            "tick",
            payload={
                "now": 10,
            },
        )
    )

    eq(
        tick.success,
        True,
        "configured scheduler service ticks",
    )

    eq(
        tick.data["tick"][
            "dispatch_count"
        ],
        2,
        "protocol tick dispatches due tasks",
    )


def main():
    cleanup()

    try:
        test_recurrence_config()
        test_task_config()
        test_defaults()
        test_codec()
        test_validator()
        test_manager_generation()
        test_due_dispatch_order()
        test_interval_completion()
        test_catch_up_behavior()
        test_event_bus_integration()
        test_persistence_round_trip()
        test_missing_event_bus()
        test_service_creation()

    finally:
        cleanup()

    print(
        "SCHEDULER CONFIG TEST SUITE: PASS"
    )
    print(
        "Assertions passed:",
        ASSERTIONS,
    )
    print(
        "Files validated: 7/7"
    )
    print(
        "Typed schedule/recurrence configuration: VALIDATED"
    )
    print(
        "Handwritten JSON decoding: VALIDATED"
    )
    print(
        "Queue target validation: VALIDATED"
    )
    print(
        "One-shot + interval dispatch: VALIDATED"
    )
    print(
        "Catch-up cadence behavior: VALIDATED"
    )
    print(
        "JobQueue priority/provenance handoff: VALIDATED"
    )
    print(
        "EventBus scheduler lifecycle integration: VALIDATED"
    )
    print(
        "Binary scheduler snapshot round trip: VALIDATED"
    )
    print(
        "SchedulerService generation: VALIDATED"
    )
    print(
        "Third-party dependencies: 0"
    )


main()
