import os

SERIAL_BASE = "libs/core/serialization/"
PROTOCOL_BASE = "libs/protocol/"
EVENT_BASE = "services/event_bus/"
QUEUE_BASE = "services/job_queue/"
SERVICE_BASE = "services/scheduler_service/"

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
    (
        QUEUE_BASE,
        [
            "job.py",
            "queue.py",
            "persistence.py",
            "manager.py",
            "worker.py",
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
    "recurrence.py",
    "schedule.py",
    "persistence.py",
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
            "scheduler_service implementation contains forbidden import: "
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

STATE_PATH = (
    "services/scheduler_service/"
    "_test_scheduler.sllmsch"
)


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
        + repr(
            actual
        )
        + " expected="
        + repr(
            expected
        )
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
            + repr(
                error
            )
        )

    raise AssertionError(
        message
        + " | expected exception was not raised"
    )


def build(
    event_bus=None,
):
    queue_manager = (
        JobQueueManager(
            event_bus=event_bus
        )
    )

    queue_manager.create_queue(
        "training",
        default_lease_seconds=10,
        default_max_attempts=3,
    )

    scheduler = SchedulerManager(
        job_queue=queue_manager,
        event_bus=event_bus,
    )

    return (
        scheduler,
        queue_manager,
    )


def test_once_schedule():
    scheduler, queue_manager = build()

    task = scheduler.create_task(
        task_id="once",
        queue_name="training",
        payload={
            "action": "train",
        },
        next_run_at=100,
    )

    early = scheduler.tick(
        99
    )

    eq(
        early[
            "dispatch_count"
        ],
        0,
        "one-shot task not dispatched early",
    )

    result = scheduler.tick(
        100
    )

    eq(
        result[
            "dispatch_count"
        ],
        1,
        "one-shot task dispatched when due",
    )

    eq(
        task.status,
        "completed",
        "one-shot task completes after dispatch",
    )

    eq(
        queue_manager.get_queue(
            "training"
        ).status()[
            "counts"
        ][
            "pending"
        ],
        1,
        "scheduler creates pending job",
    )


def test_interval_schedule():
    scheduler, queue_manager = build()

    task = scheduler.create_task(
        task_id="interval",
        queue_name="training",
        payload={
            "action": "eval",
        },
        next_run_at=10,
        recurrence=RecurrenceRule(
            mode="interval",
            interval_seconds=5,
            max_runs=3,
        ),
    )

    scheduler.tick(
        10
    )

    eq(
        task.next_run_at,
        15,
        "interval next run calculated",
    )

    scheduler.tick(
        15
    )

    eq(
        task.run_count,
        2,
        "second interval dispatch counted",
    )

    scheduler.tick(
        20
    )

    eq(
        task.status,
        "completed",
        "interval task completes at max_runs",
    )

    eq(
        queue_manager.get_queue(
            "training"
        ).status()[
            "job_count"
        ],
        3,
        "three jobs enqueued for three runs",
    )


def test_catch_up_false():
    scheduler, _ = build()

    task = scheduler.create_task(
        task_id="skip-gap",
        queue_name="training",
        payload={},
        next_run_at=10,
        recurrence=RecurrenceRule(
            mode="interval",
            interval_seconds=5,
            catch_up=False,
        ),
    )

    scheduler.tick(
        100
    )

    eq(
        task.next_run_at,
        105,
        "non-catch-up cadence schedules from dispatch time",
    )


def test_catch_up_true():
    scheduler, _ = build()

    task = scheduler.create_task(
        task_id="fixed-cadence",
        queue_name="training",
        payload={},
        next_run_at=10,
        recurrence=RecurrenceRule(
            mode="interval",
            interval_seconds=5,
            catch_up=True,
        ),
    )

    scheduler.tick(
        100
    )

    eq(
        task.next_run_at,
        15,
        "catch-up cadence retains original schedule",
    )

    second = scheduler.tick(
        100
    )

    eq(
        second[
            "dispatch_count"
        ],
        1,
        "one overdue catch-up run dispatched per tick",
    )

    eq(
        task.next_run_at,
        20,
        "catch-up advances one interval per tick",
    )


def test_end_at():
    scheduler, _ = build()

    task = scheduler.create_task(
        task_id="bounded",
        queue_name="training",
        payload={},
        next_run_at=10,
        recurrence=RecurrenceRule(
            mode="interval",
            interval_seconds=5,
            end_at=15,
        ),
    )

    scheduler.tick(
        10
    )

    eq(
        task.next_run_at,
        15,
        "end_at allows scheduled boundary",
    )

    scheduler.tick(
        15
    )

    eq(
        task.status,
        "completed",
        "task completes when next interval exceeds end_at",
    )


def test_disabled_task():
    scheduler, _ = build()

    scheduler.create_task(
        task_id="disabled",
        queue_name="training",
        payload={},
        next_run_at=1,
        enabled=False,
    )

    eq(
        scheduler.tick(
            10
        )[
            "dispatch_count"
        ],
        0,
        "disabled task is not dispatched",
    )

    scheduler.enable_task(
        "disabled"
    )

    eq(
        scheduler.tick(
            10
        )[
            "dispatch_count"
        ],
        1,
        "enabled overdue task dispatches",
    )


def test_reschedule_completed():
    scheduler, _ = build()

    task = scheduler.create_task(
        task_id="once",
        queue_name="training",
        payload={},
        next_run_at=1,
    )

    scheduler.tick(
        1
    )

    expect_error(
        RuntimeError,
        lambda: scheduler.reschedule_task(
            "once",
            10,
        ),
        "completed task requires explicit reset",
    )

    scheduler.reschedule_task(
        "once",
        10,
        reset_completed=True,
    )

    eq(
        task.status,
        "scheduled",
        "completed task explicitly reactivated",
    )

    eq(
        task.next_run_at,
        10,
        "reactivated task rescheduled",
    )


def test_deterministic_due_order():
    scheduler, queue_manager = build()

    scheduler.create_task(
        "later-sequence",
        "training",
        {
            "task": "a",
        },
        next_run_at=10,
    )

    scheduler.create_task(
        "earlier-time",
        "training",
        {
            "task": "b",
        },
        next_run_at=5,
    )

    scheduler.create_task(
        "same-time-third",
        "training",
        {
            "task": "c",
        },
        next_run_at=10,
    )

    result = scheduler.tick(
        10
    )

    eq(
        [
            item[
                "task_id"
            ]
            for item
            in result[
                "dispatched"
            ]
        ],
        [
            "earlier-time",
            "later-sequence",
            "same-time-third",
        ],
        "due tasks ordered by scheduled time then task sequence",
    )

    jobs = queue_manager.list_jobs(
        "training"
    )

    eq(
        [
            item[
                "metadata"
            ][
                "scheduler_task_id"
            ]
            for item
            in jobs
        ],
        [
            "earlier-time",
            "later-sequence",
            "same-time-third",
        ],
        "job queue receives scheduler dispatch order",
    )


def test_job_options_propagate():
    scheduler, queue_manager = build()

    scheduler.create_task(
        task_id="opts",
        queue_name="training",
        payload={
            "kind": "train",
        },
        next_run_at=1,
        priority=9,
        max_attempts=5,
        metadata={
            "owner": "scheduler",
        },
    )

    scheduler.tick(
        1
    )

    job = queue_manager.list_jobs(
        "training"
    )[0]

    eq(
        job[
            "priority"
        ],
        9,
        "scheduled priority propagated to job",
    )

    eq(
        job[
            "max_attempts"
        ],
        5,
        "scheduled max_attempts propagated to job",
    )

    eq(
        job[
            "metadata"
        ][
            "owner"
        ],
        "scheduler",
        "scheduled metadata propagated",
    )

    eq(
        job[
            "metadata"
        ][
            "scheduler_run_number"
        ],
        1,
        "scheduler run number attached",
    )


def test_dispatch_failure_isolation():
    scheduler, queue_manager = build()

    scheduler.create_task(
        "valid",
        "training",
        {},
        next_run_at=1,
    )

    broken = scheduler.create_task(
        "broken",
        "training",
        {},
        next_run_at=1,
    )

    broken.queue_name = (
        "missing-queue"
    )

    result = scheduler.tick(
        1
    )

    eq(
        result[
            "dispatch_count"
        ],
        1,
        "valid due task dispatched despite later failure",
    )

    eq(
        result[
            "failure_count"
        ],
        1,
        "broken task failure isolated",
    )

    eq(
        broken.status,
        "scheduled",
        "failed dispatch does not advance schedule",
    )

    eq(
        queue_manager.get_queue(
            "training"
        ).status()[
            "job_count"
        ],
        1,
        "only valid task created job",
    )


def test_event_bus_integration():
    event_bus = EventBusManager()

    seen = []

    event_bus.subscribe(
        "scheduler-events",
        "scheduler.",
        lambda event: seen.append(
            event.topic
        ),
        mode="prefix",
    )

    event_bus.subscribe(
        "job-events",
        "job.",
        lambda event: seen.append(
            event.topic
        ),
        mode="prefix",
    )

    scheduler, _ = build(
        event_bus=event_bus
    )

    scheduler.create_task(
        "task",
        "training",
        {},
        next_run_at=1,
    )

    scheduler.tick(
        1,
        trace_id="trace-scheduler",
    )

    eq(
        seen,
        [
            "job.enqueued",
            "scheduler.dispatched",
        ],
        "scheduler + queue lifecycle events published",
    )

    history = event_bus.history(
        topic=(
            "scheduler.dispatched"
        )
    )

    eq(
        history[
            "events"
        ][0][
            "trace_id"
        ],
        "trace-scheduler",
        "scheduler trace propagated to event bus",
    )


def test_persistence_round_trip():
    if os.path.exists(
        STATE_PATH
    ):
        os.remove(
            STATE_PATH
        )

    scheduler, queue_manager = build()

    scheduler.create_task(
        "interval",
        "training",
        {
            "kind": "train",
        },
        next_run_at=10,
        recurrence=RecurrenceRule(
            mode="interval",
            interval_seconds=10,
            max_runs=3,
        ),
        priority=2,
        metadata={
            "model": "sirellm",
        },
    )

    scheduler.tick(
        10
    )

    before = scheduler.export_state()

    saved = scheduler.save_state(
        STATE_PATH
    )

    check(
        saved[
            "bytes"
        ] > 0,
        "scheduler snapshot written",
    )

    restored = SchedulerManager(
        job_queue=queue_manager
    )

    restored.load_state_file(
        STATE_PATH
    )

    eq(
        restored.export_state(),
        before,
        "scheduler state exact round trip",
    )

    eq(
        restored.get_task(
            "interval"
        ).next_run_at,
        20,
        "restored next run preserved",
    )


def test_persistence_corruption():
    scheduler, _ = build()

    scheduler.save_state(
        STATE_PATH
    )

    handle = open(
        STATE_PATH,
        "rb",
    )

    try:
        data = bytearray(
            handle.read()
        )
    finally:
        handle.close()

    data[
        -1
    ] ^= 0x01

    handle = open(
        STATE_PATH,
        "wb",
    )

    try:
        handle.write(
            data
        )
    finally:
        handle.close()

    new_scheduler, _ = build()

    expect_error(
        ValueError,
        lambda: new_scheduler.load_state_file(
            STATE_PATH
        ),
        "scheduler checksum detects corruption",
    )


def test_status():
    scheduler, _ = build()

    scheduler.create_task(
        "scheduled",
        "training",
        {},
        next_run_at=10,
    )

    scheduler.create_task(
        "disabled",
        "training",
        {},
        next_run_at=10,
        enabled=False,
    )

    scheduler.create_task(
        "completed",
        "training",
        {},
        next_run_at=1,
    )

    scheduler.tick(
        1
    )

    status = scheduler.status()

    eq(
        status[
            "task_count"
        ],
        3,
        "scheduler status task count",
    )

    eq(
        status[
            "counts"
        ][
            "scheduled"
        ],
        1,
        "scheduler status scheduled count",
    )

    eq(
        status[
            "counts"
        ][
            "disabled"
        ],
        1,
        "scheduler status disabled count",
    )

    eq(
        status[
            "counts"
        ][
            "completed"
        ],
        1,
        "scheduler status completed count",
    )


def test_service_flow():
    scheduler, queue_manager = build()

    service = SchedulerService(
        scheduler
    )

    created = service.handle(
        ServiceRequest(
            "s1",
            "scheduler_service",
            "create_task",
            payload={
                "task_id": "task-1",
                "queue_name": (
                    "training"
                ),
                "payload": {
                    "action": "train",
                },
                "next_run_at": 100,
                "mode": "interval",
                "interval_seconds": 60,
                "max_runs": 2,
            },
        )
    )

    eq(
        created.success,
        True,
        "scheduler service creates task",
    )

    ticked = service.handle(
        ServiceRequest(
            "s2",
            "scheduler_service",
            "tick",
            payload={
                "now": 100,
            },
            trace_id=(
                "trace-service-scheduler"
            ),
        )
    )

    eq(
        ticked.data[
            "tick"
        ][
            "dispatch_count"
        ],
        1,
        "scheduler service tick dispatches due task",
    )

    eq(
        queue_manager.get_queue(
            "training"
        ).status()[
            "job_count"
        ],
        1,
        "service tick creates queue job",
    )


def test_protocol_round_trip():
    scheduler, _ = build()

    service = SchedulerService(
        scheduler
    )

    codec = ProtocolCodec()

    request = ServiceRequest(
        "protocol-scheduler",
        "scheduler_service",
        "create_task",
        payload={
            "task_id": "protocol-task",
            "queue_name": "training",
            "payload": {
                "kind": "evaluation",
            },
            "next_run_at": 5,
            "mode": "once",
        },
        trace_id="trace-scheduler",
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
        "scheduler create survives protocol codec",
    )

    eq(
        response.trace_id,
        "trace-scheduler",
        "scheduler trace preserved",
    )

    eq(
        response.data[
            "task"
        ][
            "payload"
        ][
            "kind"
        ],
        "evaluation",
        "scheduled payload survives protocol",
    )


def test_errors():
    scheduler, _ = build()

    service = SchedulerService(
        scheduler
    )

    missing = service.handle(
        ServiceRequest(
            "m",
            "scheduler_service",
            "get_task",
            payload={
                "task_id": "missing",
            },
        )
    )

    eq(
        missing.error.code,
        "NOT_FOUND",
        "missing task maps to NOT_FOUND",
    )

    invalid = service.handle(
        ServiceRequest(
            "i",
            "scheduler_service",
            "create_task",
            payload={
                "task_id": "bad",
                "queue_name": "training",
                "payload": {},
                "next_run_at": 1,
                "mode": "interval",
                "interval_seconds": 0,
            },
        )
    )

    eq(
        invalid.error.code,
        "INVALID_REQUEST",
        "invalid recurrence maps to INVALID_REQUEST",
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
    scheduler, _ = build()

    expect_error(
        KeyError,
        lambda: scheduler.create_task(
            "missing-queue",
            "does-not-exist",
            {},
            1,
        ),
        "scheduler requires existing target queue",
    )

    scheduler.create_task(
        "x",
        "training",
        {},
        1,
    )

    expect_error(
        ValueError,
        lambda: scheduler.create_task(
            "x",
            "training",
            {},
            2,
        ),
        "duplicate scheduled task rejected",
    )

    expect_error(
        ValueError,
        lambda: RecurrenceRule(
            mode="interval",
            interval_seconds=-1,
        ),
        "invalid interval rejected",
    )


def main():
    try:
        test_once_schedule()
        test_interval_schedule()
        test_catch_up_false()
        test_catch_up_true()
        test_end_at()
        test_disabled_task()
        test_reschedule_completed()
        test_deterministic_due_order()
        test_job_options_propagate()
        test_dispatch_failure_isolation()
        test_event_bus_integration()
        test_persistence_round_trip()
        test_persistence_corruption()
        test_status()
        test_service_flow()
        test_protocol_round_trip()
        test_errors()
        test_validation()

    finally:
        if os.path.exists(
            STATE_PATH
        ):
            os.remove(
                STATE_PATH
            )

    print(
        "SCHEDULER SERVICE TEST SUITE: PASS"
    )
    print(
        "Assertions passed:",
        ASSERTIONS,
    )
    print(
        "Files validated: 5/5"
    )
    print(
        "One-shot/interval scheduling: VALIDATED"
    )
    print(
        "Catch-up/fixed-cadence behavior: VALIDATED"
    )
    print(
        "Deterministic due-task ordering: VALIDATED"
    )
    print(
        "Job-queue dispatch integration: VALIDATED"
    )
    print(
        "Dispatch failure isolation: VALIDATED"
    )
    print(
        "Event-bus lifecycle publication: VALIDATED"
    )
    print(
        "Checksum-protected scheduler persistence: VALIDATED"
    )
    print(
        "Protocol service operations: VALIDATED"
    )
    print(
        "Third-party dependencies: 0"
    )


main()
