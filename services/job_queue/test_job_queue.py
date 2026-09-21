import os

SERIAL_BASE = "libs/core/serialization/"
PROTOCOL_BASE = "libs/protocol/"
EVENT_BASE = "services/event_bus/"
SERVICE_BASE = "services/job_queue/"

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
    "job.py",
    "queue.py",
    "persistence.py",
    "manager.py",
    "worker.py",
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
            "job_queue implementation contains forbidden import: "
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
    "services/job_queue/"
    "_test_job_queue.sllmjq"
)


def check(
    condition,
    message,
):
    global ASSERTIONS
    ASSERTIONS += 1

    if not condition:
        raise AssertionError(message)


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


def manager(
    event_bus=None,
):
    worker = JobQueueManager(
        event_bus=event_bus
    )

    worker.create_queue(
        "training",
        default_lease_seconds=10,
        default_max_attempts=3,
    )

    return worker


def test_priority_fifo():
    worker = manager()

    first = worker.enqueue(
        "training",
        {"name": "first"},
        now=1,
        priority=1,
    )

    second = worker.enqueue(
        "training",
        {"name": "second"},
        now=1,
        priority=10,
    )

    third = worker.enqueue(
        "training",
        {"name": "third"},
        now=1,
        priority=10,
    )

    claim_1 = worker.claim(
        "training",
        "w1",
        now=1,
    )

    eq(
        claim_1.job_id,
        second.job_id,
        "highest-priority job claimed first",
    )

    worker.complete(
        "training",
        claim_1.job_id,
        "w1",
        now=2,
    )

    claim_2 = worker.claim(
        "training",
        "w1",
        now=2,
    )

    eq(
        claim_2.job_id,
        third.job_id,
        "equal priority resolves FIFO",
    )

    check(
        first.status == "pending",
        "lower priority still pending",
    )


def test_delayed_job():
    worker = manager()

    delayed = worker.enqueue(
        "training",
        {"x": 1},
        now=10,
        available_at=20,
    )

    eq(
        worker.claim(
            "training",
            "w",
            now=19,
        ),
        None,
        "delayed job not claimable early",
    )

    claimed = worker.claim(
        "training",
        "w",
        now=20,
    )

    eq(
        claimed.job_id,
        delayed.job_id,
        "delayed job claimable at available_at",
    )


def test_complete_owner():
    worker = manager()

    job = worker.enqueue(
        "training",
        {},
        now=1,
    )

    worker.claim(
        "training",
        "owner",
        now=1,
    )

    expect_error(
        PermissionError,
        lambda: worker.complete(
            "training",
            job.job_id,
            "other",
            now=2,
        ),
        "non-owner cannot complete lease",
    )

    completed = worker.complete(
        "training",
        job.job_id,
        "owner",
        now=2,
        result={
            "loss": 0.1,
        },
    )

    eq(
        completed.status,
        "completed",
        "owner completes job",
    )

    eq(
        completed.result[
            "loss"
        ],
        0.1,
        "completion result stored",
    )


def test_retry_and_dead_letter():
    worker = manager()

    job = worker.enqueue(
        "training",
        {},
        now=1,
        max_attempts=2,
    )

    worker.claim(
        "training",
        "w",
        now=1,
    )

    failed_1 = worker.fail(
        "training",
        job.job_id,
        "w",
        now=2,
        error_message="first failure",
        retry_delay_seconds=5,
    )

    eq(
        failed_1.status,
        "pending",
        "job requeued before max attempts",
    )

    eq(
        failed_1.available_at,
        7,
        "retry delay applied",
    )

    worker.claim(
        "training",
        "w",
        now=7,
    )

    failed_2 = worker.fail(
        "training",
        job.job_id,
        "w",
        now=8,
        error_message="second failure",
    )

    eq(
        failed_2.status,
        "dead_letter",
        "job dead-lettered at max attempts",
    )

    eq(
        worker.get_queue(
            "training"
        ).status()[
            "dead_lettered_total"
        ],
        1,
        "dead-letter total counted",
    )


def test_lease_recovery():
    worker = manager()

    job = worker.enqueue(
        "training",
        {},
        now=1,
        max_attempts=3,
    )

    worker.claim(
        "training",
        "worker-a",
        now=1,
        lease_seconds=5,
    )

    recovered = worker.recover_expired(
        "training",
        now=6,
        retry_delay_seconds=2,
    )

    eq(
        recovered[
            "recovered_job_ids"
        ],
        [
            job.job_id,
        ],
        "expired lease requeued",
    )

    eq(
        worker.get_job(
            "training",
            job.job_id,
        ).available_at,
        8,
        "lease recovery delay applied",
    )

    eq(
        worker.claim(
            "training",
            "worker-b",
            now=7,
        ),
        None,
        "recovered job respects delay",
    )

    claim = worker.claim(
        "training",
        "worker-b",
        now=8,
    )

    eq(
        claim.worker_id,
        "worker-b",
        "recovered job claimable by new worker",
    )


def test_lease_expiry_dead_letter():
    worker = manager()

    job = worker.enqueue(
        "training",
        {},
        now=1,
        max_attempts=1,
    )

    worker.claim(
        "training",
        "w",
        now=1,
        lease_seconds=3,
    )

    result = worker.recover_expired(
        "training",
        now=4,
    )

    eq(
        result[
            "dead_letter_job_ids"
        ],
        [
            job.job_id,
        ],
        "expired final attempt dead-lettered",
    )


def test_cancel_retry():
    worker = manager()

    job = worker.enqueue(
        "training",
        {},
        now=1,
    )

    cancelled = worker.cancel(
        "training",
        job.job_id,
        now=2,
    )

    eq(
        cancelled.status,
        "cancelled",
        "pending job cancelled",
    )

    retried = worker.retry(
        "training",
        job.job_id,
        now=3,
        delay_seconds=2,
        reset_attempts=True,
    )

    eq(
        retried.status,
        "pending",
        "cancelled job manually retried",
    )

    eq(
        retried.available_at,
        5,
        "manual retry delay applied",
    )


def test_worker_success():
    worker = manager()

    job = worker.enqueue(
        "training",
        {
            "value": 4,
        },
        now=1,
    )

    runtime = JobWorker(
        worker_id="local-worker",
        queue_name="training",
        manager=worker,
        handler=(
            lambda claimed: {
                "double": (
                    claimed.payload[
                        "value"
                    ]
                    * 2
                )
            }
        ),
    )

    result = runtime.run_once(
        now=1,
        completion_now=2,
    )

    eq(
        result[
            "success"
        ],
        True,
        "local worker completes job",
    )

    eq(
        result[
            "result"
        ][
            "double"
        ],
        8,
        "worker handler result stored",
    )

    eq(
        worker.get_job(
            "training",
            job.job_id,
        ).status,
        "completed",
        "worker updates queue state",
    )


def test_worker_failure():
    worker = manager()

    job = worker.enqueue(
        "training",
        {},
        now=1,
        max_attempts=2,
    )

    def failing(
        claimed,
    ):
        raise RuntimeError(
            "handler failed"
        )

    runtime = JobWorker(
        worker_id="local-worker",
        queue_name="training",
        manager=worker,
        handler=failing,
        retry_delay_seconds=3,
    )

    result = runtime.run_once(
        now=1,
        completion_now=2,
    )

    eq(
        result[
            "success"
        ],
        False,
        "worker handler failure isolated",
    )

    eq(
        worker.get_job(
            "training",
            job.job_id,
        ).status,
        "pending",
        "failed job scheduled for retry",
    )

    eq(
        worker.get_job(
            "training",
            job.job_id,
        ).available_at,
        5,
        "worker retry delay applied",
    )


def test_event_bus_integration():
    event_bus = EventBusManager()

    seen = []

    event_bus.subscribe(
        "job-events",
        "job.",
        lambda event: seen.append(
            (
                event.topic,
                event.payload[
                    "job_id"
                ],
            )
        ),
        mode="prefix",
    )

    worker = manager(
        event_bus=event_bus
    )

    job = worker.enqueue(
        "training",
        {},
        now=1,
        trace_id="trace-job",
    )

    worker.claim(
        "training",
        "w",
        now=1,
        trace_id="trace-job",
    )

    worker.complete(
        "training",
        job.job_id,
        "w",
        now=2,
        trace_id="trace-job",
    )

    eq(
        [
            item[0]
            for item in seen
        ],
        [
            "job.enqueued",
            "job.claimed",
            "job.completed",
        ],
        "job lifecycle published to event bus",
    )

    history = event_bus.history(
        topic="job.completed"
    )

    eq(
        history[
            "events"
        ][0][
            "trace_id"
        ],
        "trace-job",
        "job event trace propagated",
    )


def test_list_status_purge():
    worker = manager()

    completed = worker.enqueue(
        "training",
        {},
        now=1,
    )

    pending = worker.enqueue(
        "training",
        {},
        now=1,
    )

    worker.claim(
        "training",
        "w",
        now=1,
    )

    worker.complete(
        "training",
        completed.job_id,
        "w",
        now=2,
    )

    listed = worker.list_jobs(
        "training",
        status="pending",
    )

    eq(
        [
            item[
                "job_id"
            ]
            for item in listed
        ],
        [
            pending.job_id,
        ],
        "job status filtering",
    )

    status = worker.status()

    eq(
        status[
            "counts"
        ][
            "completed"
        ],
        1,
        "manager completed count",
    )

    purged = worker.purge_terminal(
        "training"
    )

    eq(
        purged[
            "removed_count"
        ],
        1,
        "terminal purge removes completed job",
    )


def test_persistence_round_trip():
    if os.path.exists(
        STATE_PATH
    ):
        os.remove(
            STATE_PATH
        )

    source = manager()

    source.enqueue(
        "training",
        {
            "task": "train",
        },
        now=10,
        priority=4,
        metadata={
            "model": "sirellm",
        },
    )

    source.enqueue(
        "training",
        {
            "task": "eval",
        },
        now=11,
        available_at=20,
    )

    source.claim(
        "training",
        "w",
        now=12,
    )

    before = source.export_state()

    saved = source.save_state(
        STATE_PATH
    )

    check(
        saved[
            "bytes"
        ] > 0,
        "job-queue snapshot written",
    )

    restored = JobQueueManager()

    restored.load_state_file(
        STATE_PATH
    )

    eq(
        restored.export_state(),
        before,
        "job-queue snapshot exact round trip",
    )

    eq(
        restored.get_queue(
            "training"
        ).status()[
            "job_count"
        ],
        2,
        "restored queue retains jobs",
    )


def test_persistence_corruption():
    worker = manager()

    worker.save_state(
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

    expect_error(
        ValueError,
        lambda: JobQueueManager().load_state_file(
            STATE_PATH
        ),
        "job-queue checksum detects corruption",
    )


def test_service_flow():
    service = JobQueueService()

    created = service.handle(
        ServiceRequest(
            "s1",
            "job_queue",
            "create_queue",
            payload={
                "queue_name": "tasks",
            },
        )
    )

    eq(
        created.success,
        True,
        "service creates queue",
    )

    enqueued = service.handle(
        ServiceRequest(
            "s2",
            "job_queue",
            "enqueue",
            payload={
                "queue_name": "tasks",
                "payload": {
                    "kind": "embed",
                },
                "now": 100,
                "priority": 5,
            },
            trace_id="trace-service-job",
        )
    )

    job_id = enqueued.data[
        "job"
    ][
        "job_id"
    ]

    claimed = service.handle(
        ServiceRequest(
            "s3",
            "job_queue",
            "claim",
            payload={
                "queue_name": "tasks",
                "worker_id": "w1",
                "now": 100,
            },
        )
    )

    eq(
        claimed.data[
            "job"
        ][
            "job_id"
        ],
        job_id,
        "service claims enqueued job",
    )

    completed = service.handle(
        ServiceRequest(
            "s4",
            "job_queue",
            "complete",
            payload={
                "queue_name": "tasks",
                "job_id": job_id,
                "worker_id": "w1",
                "now": 101,
                "result": {
                    "ok": True,
                },
            },
        )
    )

    eq(
        completed.data[
            "job"
        ][
            "status"
        ],
        "completed",
        "service completes job",
    )


def test_protocol_round_trip():
    manager_instance = (
        JobQueueManager()
    )

    manager_instance.create_queue(
        "tasks"
    )

    service = JobQueueService(
        manager_instance
    )

    codec = ProtocolCodec()

    request = ServiceRequest(
        "protocol-job",
        "job_queue",
        "enqueue",
        payload={
            "queue_name": "tasks",
            "payload": {
                "task": "retrieve",
            },
            "now": 5,
        },
        trace_id="trace-job-queue",
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
        "job enqueue survives protocol codec",
    )

    eq(
        response.trace_id,
        "trace-job-queue",
        "job-queue trace preserved",
    )

    eq(
        response.data[
            "job"
        ][
            "payload"
        ][
            "task"
        ],
        "retrieve",
        "job payload survives protocol",
    )


def test_errors():
    service = JobQueueService()

    missing = service.handle(
        ServiceRequest(
            "m",
            "job_queue",
            "enqueue",
            payload={
                "queue_name": "missing",
                "payload": {},
                "now": 1,
            },
        )
    )

    eq(
        missing.error.code,
        "NOT_FOUND",
        "missing queue maps to NOT_FOUND",
    )

    service.handle(
        ServiceRequest(
            "c",
            "job_queue",
            "create_queue",
            payload={
                "queue_name": "q",
            },
        )
    )

    invalid = service.handle(
        ServiceRequest(
            "i",
            "job_queue",
            "enqueue",
            payload={
                "queue_name": "q",
                "payload": [],
                "now": 1,
            },
        )
    )

    eq(
        invalid.error.code,
        "INVALID_REQUEST",
        "invalid payload maps to INVALID_REQUEST",
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
    worker = manager()

    expect_error(
        ValueError,
        lambda: worker.create_queue(
            "training"
        ),
        "duplicate queue rejected",
    )

    expect_error(
        RuntimeError,
        lambda: worker.remove_queue(
            "training"
        )
        if (
            worker.enqueue(
                "training",
                {},
                now=1,
            )
        )
        else None,
        "non-empty queue removal rejected",
    )

    expect_error(
        ValueError,
        lambda: JobWorker(
            "",
            "training",
            worker,
            lambda job: None,
        ),
        "empty worker ID rejected",
    )


def main():
    try:
        test_priority_fifo()
        test_delayed_job()
        test_complete_owner()
        test_retry_and_dead_letter()
        test_lease_recovery()
        test_lease_expiry_dead_letter()
        test_cancel_retry()
        test_worker_success()
        test_worker_failure()
        test_event_bus_integration()
        test_list_status_purge()
        test_persistence_round_trip()
        test_persistence_corruption()
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
        "JOB QUEUE TEST SUITE: PASS"
    )
    print(
        "Assertions passed:",
        ASSERTIONS,
    )
    print(
        "Files validated: 6/6"
    )
    print(
        "Priority/FIFO/delayed scheduling: VALIDATED"
    )
    print(
        "Worker lease ownership/recovery: VALIDATED"
    )
    print(
        "Retry/dead-letter semantics: VALIDATED"
    )
    print(
        "Local worker success/failure handling: VALIDATED"
    )
    print(
        "Event-bus lifecycle publication: VALIDATED"
    )
    print(
        "Checksum-protected queue persistence: VALIDATED"
    )
    print(
        "Protocol service operations: VALIDATED"
    )
    print(
        "Third-party dependencies: 0"
    )


main()
