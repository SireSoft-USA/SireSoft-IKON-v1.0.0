import socket
import threading
import time

SERIAL_BASE = "libs/core/serialization/"
PROTOCOL_BASE = "libs/protocol/"
NETWORK_BASE = "runtime/networking/"
CONCURRENCY_BASE = "runtime/concurrency/"

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
    "http_parser.py",
    "tcp_server.py",
    "tcp_client.py",
    "connection_pool.py",
]:
    path = NETWORK_BASE + filename

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
    "future.py",
    "task_queue.py",
    "semaphore.py",
    "worker_pool.py",
    "service_executor.py",
    "network_runner.py",
]:
    path = CONCURRENCY_BASE + filename

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


def test_future_success():
    future = TaskFuture(
        "task-1"
    )

    eq(
        future.state(),
        "pending",
        "future starts pending",
    )

    eq(
        future.set_running(),
        True,
        "future enters running",
    )

    future.set_result(
        42
    )

    eq(
        future.result(),
        42,
        "future returns result",
    )

    eq(
        future.state(),
        "succeeded",
        "future success state",
    )


def test_future_failure():
    future = TaskFuture(
        "task-2"
    )

    future.set_running()

    error = ValueError(
        "boom"
    )

    future.set_exception(
        error
    )

    eq(
        future.exception(),
        error,
        "future exposes failure object",
    )

    expect_error(
        ValueError,
        lambda: future.result(),
        "future re-raises worker exception",
    )


def test_future_cancel():
    future = TaskFuture(
        "task-3"
    )

    eq(
        future.cancel(),
        True,
        "pending future can cancel",
    )

    eq(
        future.cancelled(),
        True,
        "future cancellation state",
    )

    expect_error(
        RuntimeError,
        lambda: future.result(),
        "cancelled future has no result",
    )


def test_queue_fifo_close():
    queue = BoundedTaskQueue(
        2
    )

    queue.put(
        "a"
    )
    queue.put(
        "b"
    )

    eq(
        queue.get(),
        "a",
        "bounded queue FIFO first",
    )

    eq(
        queue.get(),
        "b",
        "bounded queue FIFO second",
    )

    queue.close()

    eq(
        queue.get(),
        None,
        "closed empty queue returns sentinel None",
    )

    expect_error(
        QueueClosedError,
        lambda: queue.put(
            "c"
        ),
        "closed queue rejects new work",
    )


def test_queue_capacity():
    queue = BoundedTaskQueue(
        1
    )

    queue.put(
        "a"
    )

    expect_error(
        RuntimeError,
        lambda: queue.put(
            "b",
            block=False,
        ),
        "non-blocking put enforces capacity",
    )


def test_semaphore():
    semaphore = CountingSemaphore(
        2
    )

    eq(
        semaphore.acquire(
            block=False
        ),
        True,
        "first semaphore permit",
    )

    eq(
        semaphore.acquire(
            block=False
        ),
        True,
        "second semaphore permit",
    )

    eq(
        semaphore.acquire(
            block=False
        ),
        False,
        "semaphore exhausted",
    )

    eq(
        semaphore.in_use(),
        2,
        "semaphore in-use count",
    )

    semaphore.release()

    eq(
        semaphore.available(),
        1,
        "semaphore release restores permit",
    )


def test_worker_pool_parallelism():
    pool = WorkerPool(
        worker_count=3,
        queue_capacity=10,
    )

    lock = threading.Lock()

    state = {
        "active": 0,
        "max_active": 0,
    }

    gate = threading.Event()

    def task(
        value,
    ):
        with lock:
            state[
                "active"
            ] += 1

            if state[
                "active"
            ] > state[
                "max_active"
            ]:
                state[
                    "max_active"
                ] = state[
                    "active"
                ]

        gate.wait(
            timeout=2.0
        )

        with lock:
            state[
                "active"
            ] -= 1

        return (
            value
            * 2
        )

    futures = [
        pool.submit(
            task,
            index,
        )
        for index in range(
            3
        )
    ]

    deadline = (
        time.monotonic()
        + 2.0
    )

    while True:
        with lock:
            active = state[
                "active"
            ]

        if active >= 3:
            break

        if time.monotonic() >= deadline:
            break

        time.sleep(
            0.01
        )

    gate.set()

    values = [
        future.result(
            timeout=2.0
        )
        for future in futures
    ]

    pool.shutdown()

    eq(
        values,
        [
            0,
            2,
            4,
        ],
        "worker pool returns task results",
    )

    eq(
        state[
            "max_active"
        ],
        3,
        "worker pool executes up to worker_count concurrently",
    )

    eq(
        pool.status()[
            "total_succeeded"
        ],
        3,
        "worker pool success count",
    )


def test_worker_pool_failure():
    pool = WorkerPool(
        worker_count=1,
        queue_capacity=2,
    )

    def fail():
        raise RuntimeError(
            "task failure"
        )

    future = pool.submit(
        fail
    )

    expect_error(
        RuntimeError,
        lambda: future.result(
            timeout=2.0
        ),
        "worker task failure propagated",
    )

    pool.shutdown()

    eq(
        pool.status()[
            "total_failed"
        ],
        1,
        "worker pool failure count",
    )


def test_worker_pool_cancel_pending():
    pool = WorkerPool(
        worker_count=1,
        queue_capacity=4,
    )

    gate = threading.Event()

    first = pool.submit(
        lambda: gate.wait(
            timeout=2.0
        )
    )

    second = pool.submit(
        lambda: "never"
    )

    deadline = (
        time.monotonic()
        + 1.0
    )

    while not first.running():
        if time.monotonic() >= deadline:
            break

        time.sleep(
            0.01
        )

    eq(
        second.cancel(),
        True,
        "pending queued future can cancel",
    )

    gate.set()

    first.result(
        timeout=2.0
    )

    pool.shutdown()

    eq(
        second.cancelled(),
        True,
        "cancelled queued task never runs",
    )


class EchoService:
    def __init__(
        self,
        tracker=None,
    ):
        self.tracker = tracker

    def handle(
        self,
        request,
    ):
        if self.tracker is not None:
            with self.tracker[
                "lock"
            ]:
                self.tracker[
                    "active"
                ] += 1

                if (
                    self.tracker[
                        "active"
                    ]
                    > self.tracker[
                        "max"
                    ]
                ):
                    self.tracker[
                        "max"
                    ] = self.tracker[
                        "active"
                    ]

            time.sleep(
                0.03
            )

            with self.tracker[
                "lock"
            ]:
                self.tracker[
                    "active"
                ] -= 1

        return (
            ServiceResponse
            .success_response(
                request,
                data={
                    "echo": (
                        request.payload
                    ),
                },
            )
        )


def test_service_executor():
    pool = WorkerPool(
        worker_count=4,
        queue_capacity=8,
    )

    tracker = {
        "lock": threading.Lock(),
        "active": 0,
        "max": 0,
    }

    executor = ServiceExecutor(
        pool,
        EchoService(
            tracker
        ),
        max_in_flight=2,
    )

    futures = []

    for index in range(
        5
    ):
        futures.append(
            executor.submit(
                ServiceRequest(
                    (
                        "service-"
                        + str(
                            index
                        )
                    ),
                    "echo_service",
                    "echo",
                    payload={
                        "index": index,
                    },
                    trace_id=(
                        "trace-"
                        + str(
                            index
                        )
                    ),
                )
            )
        )

    responses = [
        future.result(
            timeout=3.0
        )
        for future in futures
    ]

    pool.shutdown()

    eq(
        len(
            responses
        ),
        5,
        "service executor completes all requests",
    )

    eq(
        responses[
            4
        ].data[
            "echo"
        ][
            "index"
        ],
        4,
        "service response payload preserved",
    )

    check(
        tracker[
            "max"
        ] <= 2,
        "service executor max_in_flight enforced",
    )

    eq(
        executor.status()[
            "total_succeeded"
        ],
        5,
        "service executor success count",
    )


def test_service_executor_bad_response():
    pool = WorkerPool(
        worker_count=1,
        queue_capacity=2,
    )

    executor = ServiceExecutor(
        pool,
        lambda request: {
            "not": "response"
        },
    )

    future = executor.submit(
        ServiceRequest(
            "bad-1",
            "x",
            "y",
        )
    )

    expect_error(
        TypeError,
        lambda: future.result(
            timeout=2.0
        ),
        "service executor rejects non-ServiceResponse",
    )

    pool.shutdown()

    eq(
        executor.status()[
            "total_failed"
        ],
        1,
        "service executor failure count",
    )


def client_call(
    host,
    port,
    payload,
    output,
    errors,
):
    try:
        client = TCPClient(
            host,
            port,
            timeout_seconds=3.0,
        )

        output.append(
            client.request(
                payload
            )
        )

    except Exception as error:
        errors.append(
            error
        )


def test_concurrent_tcp_runner():
    server = TCPServer(
        "127.0.0.1",
        0,
        lambda payload, address: (
            b"ok:"
            + payload
        ),
        timeout_seconds=3.0,
    )

    server.start()

    pool = WorkerPool(
        worker_count=3,
        queue_capacity=6,
    )

    runner = ConcurrentTCPRunner(
        server,
        pool,
    )

    server_futures = (
        runner.serve_connections(
            3,
            max_frames_per_connection=1,
        )
    )

    outputs = []
    errors = []

    client_threads = []

    for value in (
        b"a",
        b"b",
        b"c",
    ):
        thread = threading.Thread(
            target=client_call,
            args=(
                "127.0.0.1",
                server.port,
                value,
                outputs,
                errors,
            ),
        )

        client_threads.append(
            thread
        )
        thread.start()

    for thread in client_threads:
        thread.join(
            timeout=4.0
        )

    for future in server_futures:
        future.result(
            timeout=4.0
        )

    server.stop()
    pool.shutdown()

    eq(
        errors,
        [],
        "concurrent TCP clients complete without errors",
    )

    eq(
        sorted(
            outputs
        ),
        [
            b"ok:a",
            b"ok:b",
            b"ok:c",
        ],
        "concurrent TCP runner serves all connections",
    )

    eq(
        server.status()[
            "accepted_connections"
        ],
        3,
        "network runner accepted expected connections",
    )


def test_shutdown_rejects_submit():
    pool = WorkerPool(
        worker_count=1,
        queue_capacity=1,
    )

    pool.start()
    pool.shutdown()

    expect_error(
        RuntimeError,
        lambda: pool.submit(
            lambda: None
        ),
        "shutdown worker pool rejects new submissions",
    )


def main():
    test_future_success()
    test_future_failure()
    test_future_cancel()
    test_queue_fifo_close()
    test_queue_capacity()
    test_semaphore()
    test_worker_pool_parallelism()
    test_worker_pool_failure()
    test_worker_pool_cancel_pending()
    test_service_executor()
    test_service_executor_bad_response()
    test_concurrent_tcp_runner()
    test_shutdown_rejects_submit()

    print(
        "RUNTIME CONCURRENCY TEST SUITE: PASS"
    )
    print(
        "Assertions passed:",
        ASSERTIONS,
    )
    print(
        "Files validated: 6/6"
    )
    print(
        "Handwritten futures/state transitions: VALIDATED"
    )
    print(
        "Bounded blocking task queue/backpressure: VALIDATED"
    )
    print(
        "Counting semaphore limits: VALIDATED"
    )
    print(
        "Fixed-size worker-pool concurrency: VALIDATED"
    )
    print(
        "ServiceRequest/ServiceResponse executor integration: VALIDATED"
    )
    print(
        "Concurrent TCPServer integration: VALIDATED"
    )
    print(
        "Third-party dependencies: 0"
    )
    print(
        "Standard-library concurrency dependencies: threading, time"
    )


main()
