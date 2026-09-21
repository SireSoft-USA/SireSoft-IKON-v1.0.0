import os

SERIAL_BASE = "libs/core/serialization/"
PARSER_BASE = "libs/data/parsers/"
PROTOCOL_BASE = "libs/protocol/"
EVENT_BASE = "services/event_bus/"
QUEUE_BASE = "services/job_queue/"
CONFIG_BASE = "configs/job_queue/"

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
    "queue.py",
    "worker.py",
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
            "job queue config implementation contains forbidden import: "
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
    "configs/job_queue/"
    "_test_queue_state.sllmjq"
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


def cleanup():
    if os.path.isfile(
        STATE_PATH
    ):
        os.remove(
            STATE_PATH
        )


class JobHandler:
    def __init__(
        self,
    ):
        self.calls = []

    def handle_job(
        self,
        job,
    ):
        self.calls.append(
            job.job_id
        )

        if job.payload.get(
            "fail"
        ):
            raise RuntimeError(
                "simulated job failure"
            )

        return {
            "handled": (
                job.payload.get(
                    "value"
                )
            ),
        }


def sample_config(
    event_bus=False,
):
    return JobQueueConfig(
        queues=[
            JobQueueDefinitionConfig(
                "training",
                default_lease_seconds=20,
                default_max_attempts=2,
            ),
            JobQueueDefinitionConfig(
                "maintenance",
                default_lease_seconds=10,
                default_max_attempts=3,
            ),
            JobQueueDefinitionConfig(
                "disabled",
                enabled=False,
            ),
        ],
        workers=[
            JobWorkerConfig(
                worker_id="trainer-1",
                queue_name="training",
                handler_key="trainer",
                lease_seconds=15,
                retry_delay_seconds=5,
            ),
        ],
        attach_event_bus=event_bus,
    )


def test_queue_config():
    config = (
        JobQueueDefinitionConfig(
            "training",
            20,
            2,
        )
    )

    eq(
        config.default_lease_seconds,
        20,
        "queue lease stored",
    )

    expect_error(
        ValueError,
        lambda: (
            JobQueueDefinitionConfig(
                "x",
                default_lease_seconds=0,
            )
        ),
        "invalid queue lease rejected",
    )


def test_worker_config():
    worker = JobWorkerConfig(
        "w1",
        "training",
        "handler",
        retry_delay_seconds=4,
    )

    eq(
        worker.retry_delay_seconds,
        4,
        "worker retry delay stored",
    )

    expect_error(
        ValueError,
        lambda: JobWorkerConfig(
            "",
            "training",
            "handler",
        ),
        "empty worker ID rejected",
    )


def test_defaults():
    config = (
        default_job_queue_config()
    )

    eq(
        len(
            config.queues
        ),
        4,
        "default queue topology includes four queues",
    )

    eq(
        config.attach_event_bus,
        True,
        "default queue config attaches event bus",
    )


def test_codec():
    text = (
        '{"queues":['
        '{"queue_name":"training",'
        '"default_lease_seconds":45,'
        '"default_max_attempts":4}'
        '],'
        '"workers":['
        '{"worker_id":"w1",'
        '"queue_name":"training",'
        '"handler_key":"trainer",'
        '"lease_seconds":20,'
        '"retry_delay_seconds":3}'
        '],'
        '"attach_event_bus":false,'
        '"metadata":{"profile":"prod"}'
        '}'
    )

    config = (
        JobQueueConfigCodec()
        .decode_text(
            text
        )
    )

    eq(
        config.queues[
            0
        ].default_lease_seconds,
        45,
        "codec queue lease",
    )

    eq(
        config.workers[
            0
        ].handler_key,
        "trainer",
        "codec worker handler key",
    )


def test_validator():
    config = JobQueueConfig(
        queues=[
            JobQueueDefinitionConfig(
                "training",
                enabled=False,
            ),
            JobQueueDefinitionConfig(
                "maintenance",
                enabled=True,
            ),
        ],
        workers=[
            JobWorkerConfig(
                "w1",
                "training",
                "handler",
            ),
        ],
    )

    result = (
        JobQueueConfigValidator()
        .validate(
            config
        )
    )

    eq(
        result[
            "valid"
        ],
        False,
        "worker cannot target disabled queue",
    )

    eq(
        result[
            "errors"
        ][0][
            "code"
        ],
        "WORKER_QUEUE_UNAVAILABLE",
        "worker queue validation code",
    )


def test_initialize():
    handler = JobHandler()

    result = (
        JobQueueConfigFactory()
        .initialize(
            sample_config(),
            handlers={
                "trainer": handler,
            },
        )
    )

    eq(
        result[
            "queue_count"
        ],
        2,
        "disabled queue excluded",
    )

    eq(
        result[
            "worker_count"
        ],
        1,
        "configured worker created",
    )

    eq(
        result[
            "manager"
        ].get_queue(
            "training"
        ).default_max_attempts,
        2,
        "queue retry default applied",
    )


def test_priority_and_fifo():
    manager = (
        JobQueueConfigFactory()
        .initialize(
            sample_config(),
            handlers={
                "trainer": (
                    JobHandler()
                ),
            },
        )[
            "manager"
        ]
    )

    first = manager.enqueue(
        "training",
        {
            "value": "low",
        },
        now=1,
        priority=0,
        job_id="low",
    )

    second = manager.enqueue(
        "training",
        {
            "value": "high-a",
        },
        now=2,
        priority=5,
        job_id="high-a",
    )

    third = manager.enqueue(
        "training",
        {
            "value": "high-b",
        },
        now=3,
        priority=5,
        job_id="high-b",
    )

    claimed = manager.claim(
        "training",
        "worker",
        now=3,
    )

    eq(
        claimed.job_id,
        second.job_id,
        "higher priority claimed before earlier low-priority job",
    )

    manager.complete(
        "training",
        claimed.job_id,
        "worker",
        now=3,
    )

    claimed2 = manager.claim(
        "training",
        "worker",
        now=3,
    )

    eq(
        claimed2.job_id,
        third.job_id,
        "equal priority preserves FIFO sequence",
    )


def test_worker_success():
    handler = JobHandler()

    result = (
        JobQueueConfigFactory()
        .initialize(
            sample_config(),
            handlers={
                "trainer": handler,
            },
        )
    )

    manager = result[
        "manager"
    ]
    worker = result[
        "workers"
    ][0]

    manager.enqueue(
        "training",
        {
            "value": "model-a",
        },
        now=10,
        job_id="job-success",
    )

    run = worker.run_once(
        now=10,
        completion_now=11,
    )

    eq(
        run[
            "success"
        ],
        True,
        "configured worker completes successful job",
    )

    eq(
        run[
            "result"
        ][
            "handled"
        ],
        "model-a",
        "worker handler result persisted",
    )

    eq(
        worker.status()[
            "succeeded"
        ],
        1,
        "worker success metric updated",
    )


def test_worker_retry_and_dead_letter():
    handler = JobHandler()

    result = (
        JobQueueConfigFactory()
        .initialize(
            sample_config(),
            handlers={
                "trainer": handler,
            },
        )
    )

    manager = result[
        "manager"
    ]
    worker = result[
        "workers"
    ][0]

    manager.enqueue(
        "training",
        {
            "fail": True,
        },
        now=20,
        max_attempts=2,
        job_id="job-fail",
    )

    first = worker.run_once(
        20,
        completion_now=21,
    )

    eq(
        first[
            "job"
        ][
            "status"
        ],
        "pending",
        "first failure schedules retry",
    )

    eq(
        first[
            "job"
        ][
            "available_at"
        ],
        26,
        "configured worker retry delay applied",
    )

    second = worker.run_once(
        26,
        completion_now=27,
    )

    eq(
        second[
            "job"
        ][
            "status"
        ],
        "dead_letter",
        "second failure reaches configured max attempts",
    )


def test_lease_recovery():
    manager = (
        JobQueueConfigFactory()
        .initialize(
            sample_config(),
            handlers={
                "trainer": (
                    JobHandler()
                ),
            },
        )[
            "manager"
        ]
    )

    manager.enqueue(
        "maintenance",
        {
            "task": "cleanup",
        },
        now=100,
        max_attempts=2,
        job_id="lease-job",
    )

    manager.claim(
        "maintenance",
        "w1",
        now=100,
        lease_seconds=5,
    )

    recovered = (
        manager.recover_expired(
            "maintenance",
            now=105,
            retry_delay_seconds=2,
        )
    )

    eq(
        recovered[
            "recovered_count"
        ],
        1,
        "expired lease recovered",
    )

    eq(
        manager.get_job(
            "maintenance",
            "lease-job",
        ).available_at,
        107,
        "recovery retry delay applied",
    )


def test_event_bus_integration():
    event_bus = EventBusManager(
        max_history=20
    )

    result = (
        JobQueueConfigFactory()
        .initialize(
            sample_config(
                event_bus=True
            ),
            event_bus=event_bus,
            handlers={
                "trainer": (
                    JobHandler()
                ),
            },
        )
    )

    manager = result[
        "manager"
    ]

    manager.enqueue(
        "training",
        {
            "value": "x",
        },
        now=1,
        job_id="evt-job",
        trace_id="trace-1",
        correlation_id="corr-1",
    )

    worker = result[
        "workers"
    ][0]

    worker.run_once(
        now=1,
        completion_now=2,
        trace_id="trace-1",
        correlation_id="corr-1",
    )

    history = event_bus.history(
        limit=10
    )

    topics = [
        event[
            "topic"
        ]
        for event
        in history[
            "events"
        ]
    ]

    eq(
        topics,
        [
            "job.enqueued",
            "job.claimed",
            "job.completed",
        ],
        "job lifecycle publishes to configured event bus",
    )

    eq(
        history[
            "events"
        ][0][
            "trace_id"
        ],
        "trace-1",
        "job lifecycle preserves trace metadata",
    )


def test_persistence_round_trip():
    cleanup()

    manager = (
        JobQueueConfigFactory()
        .initialize(
            sample_config(),
            handlers={
                "trainer": (
                    JobHandler()
                ),
            },
        )[
            "manager"
        ]
    )

    manager.enqueue(
        "training",
        {
            "value": "persist",
        },
        now=5,
        priority=3,
        job_id="persist-job",
    )

    artifact = manager.save_state(
        STATE_PATH
    )

    check(
        artifact[
            "bytes"
        ] > 0,
        "job queue snapshot persisted",
    )

    load_config = JobQueueConfig(
        queues=[
            JobQueueDefinitionConfig(
                "placeholder"
            ),
        ],
        workers=[],
        attach_event_bus=False,
        state_path=STATE_PATH,
        load_state_on_start=True,
    )

    loaded = (
        JobQueueConfigFactory()
        .initialize(
            load_config,
        )[
            "manager"
        ]
    )

    eq(
        loaded.export_state(),
        manager.export_state(),
        "configured state load reproduces exact queue state",
    )


def test_missing_event_bus():
    expect_error(
        ValueError,
        lambda: (
            JobQueueConfigFactory()
            .initialize(
                sample_config(
                    event_bus=True
                ),
                handlers={
                    "trainer": (
                        JobHandler()
                    ),
                },
            )
        ),
        "required event bus dependency enforced",
    )


def test_missing_worker_handler():
    expect_error(
        KeyError,
        lambda: (
            JobQueueConfigFactory()
            .initialize(
                sample_config(),
                handlers={},
            )
        ),
        "missing worker handler rejected",
    )


def test_service_creation():
    service = (
        JobQueueConfigFactory()
        .build_service(
            sample_config(),
            handlers={
                "trainer": (
                    JobHandler()
                ),
            },
        )
    )

    check(
        isinstance(
            service,
            JobQueueService,
        ),
        "factory creates JobQueueService",
    )

    enqueue = service.handle(
        ServiceRequest(
            "jq-enqueue",
            "job_queue",
            "enqueue",
            payload={
                "queue_name": (
                    "maintenance"
                ),
                "payload": {
                    "task": "compact",
                },
                "now": 10,
                "job_id": (
                    "service-job"
                ),
            },
        )
    )

    eq(
        enqueue.success,
        True,
        "configured job queue service enqueues",
    )

    claim = service.handle(
        ServiceRequest(
            "jq-claim",
            "job_queue",
            "claim",
            payload={
                "queue_name": (
                    "maintenance"
                ),
                "worker_id": "manual",
                "now": 10,
            },
        )
    )

    eq(
        claim.success,
        True,
        "configured job queue service claims",
    )

    eq(
        claim.data[
            "job"
        ][
            "job_id"
        ],
        "service-job",
        "protocol claim returns queued job",
    )


def main():
    cleanup()

    try:
        test_queue_config()
        test_worker_config()
        test_defaults()
        test_codec()
        test_validator()
        test_initialize()
        test_priority_and_fifo()
        test_worker_success()
        test_worker_retry_and_dead_letter()
        test_lease_recovery()
        test_event_bus_integration()
        test_persistence_round_trip()
        test_missing_event_bus()
        test_missing_worker_handler()
        test_service_creation()

    finally:
        cleanup()

    print(
        "JOB QUEUE CONFIG TEST SUITE: PASS"
    )
    print(
        "Assertions passed:",
        ASSERTIONS,
    )
    print(
        "Files validated: 7/7"
    )
    print(
        "Typed queue/worker topology: VALIDATED"
    )
    print(
        "Handwritten JSON decoding: VALIDATED"
    )
    print(
        "Priority + FIFO scheduling: VALIDATED"
    )
    print(
        "Worker success/retry/dead-letter flow: VALIDATED"
    )
    print(
        "Lease expiry recovery: VALIDATED"
    )
    print(
        "EventBus lifecycle integration: VALIDATED"
    )
    print(
        "Binary snapshot round trip: VALIDATED"
    )
    print(
        "JobQueueService generation: VALIDATED"
    )
    print(
        "Third-party dependencies: 0"
    )


main()
