import threading
import time

PROTOCOL_BASE = "libs/protocol/"
LOAD_BALANCER_BASE = "services/load_balancer/"
DISCOVERY_BASE = "services/service_discovery/"
HOST_BASE = "runtime/service_host/"
MAINTENANCE_BASE = "runtime/maintenance/"

namespace = {
    "__builtins__": __builtins__,
}

groups = [
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
        LOAD_BALANCER_BASE,
        [
            "instance.py",
            "registry.py",
            "strategies.py",
            "load_balancer.py",
        ],
    ),
    (
        DISCOVERY_BASE,
        [
            "descriptor.py",
            "registry.py",
            "manager.py",
        ],
    ),
    (
        HOST_BASE,
        [
            "binding.py",
            "registry.py",
            "host.py",
            "gateway_dispatcher.py",
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
    "state.py",
    "snapshot.py",
    "drain.py",
    "manager.py",
    "dispatcher.py",
]:
    path = (
        MAINTENANCE_BASE
        + filename
    )

    source = open(
        path,
        "r",
        encoding="utf-8",
    ).read()

    if "import " in source:
        raise AssertionError(
            "maintenance implementation contains forbidden import: "
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


def echo_handler(
    request,
):
    return (
        ServiceResponse
        .success_response(
            request,
            data={
                "ok": True,
            },
        )
    )


def build_host():
    host = ServiceHost()

    host.add_service(
        "echo-1",
        "echo_service",
        echo_handler,
    )

    host.add_service(
        "echo-2",
        "echo_service",
        echo_handler,
    )

    host.start(
        1
    )

    return host


def test_state():
    state = MaintenanceState()

    eq(
        state.mode,
        "normal",
        "maintenance state starts normal",
    )

    state.transition(
        "draining",
        5,
        reason="deploy",
    )

    eq(
        state.accepting_requests(),
        False,
        "draining state rejects new requests",
    )

    state.transition(
        "maintenance",
        6,
        reason="deploy",
    )

    eq(
        state.transition_count,
        2,
        "state transition count",
    )

    expect_error(
        ValueError,
        lambda: state.transition(
            "normal",
            4,
        ),
        "maintenance time cannot move backwards",
    )


def test_enter_maintenance_when_idle():
    host = build_host()

    manager = RuntimeMaintenanceManager(
        host
    )

    status = manager.enter(
        10,
        reason="upgrade",
    )

    eq(
        status[
            "mode"
        ],
        "maintenance",
        "idle host enters maintenance immediately",
    )

    eq(
        status[
            "drain"
        ][
            "drained"
        ],
        True,
        "idle host is drained",
    )

    eq(
        host.load_balancer
        .registry
        .count(
            available_only=True
        ),
        0,
        "maintenance removes instances from traffic",
    )

    manager.exit(
        11
    )

    eq(
        host.load_balancer
        .registry
        .count(
            available_only=True
        ),
        2,
        "exit maintenance restores traffic",
    )

    host.stop()


def test_dispatcher_codes():
    host = build_host()

    manager = RuntimeMaintenanceManager(
        host
    )

    dispatcher = MaintenanceDispatcher(
        manager,
        host.dispatch,
    )

    normal = dispatcher(
        ServiceRequest(
            "r1",
            "echo_service",
            "echo",
        )
    )

    eq(
        normal.success,
        True,
        "normal mode dispatches request",
    )

    manager.begin_draining(
        20,
        reason="deploy",
    )

    draining = dispatcher(
        ServiceRequest(
            "r2",
            "echo_service",
            "echo",
        )
    )

    eq(
        draining.error.code,
        "RUNTIME_DRAINING",
        "draining returns explicit protocol error",
    )

    manager.advance(
        20
    )

    maintenance = dispatcher(
        ServiceRequest(
            "r3",
            "echo_service",
            "echo",
        )
    )

    eq(
        maintenance.error.code,
        "RUNTIME_MAINTENANCE",
        "maintenance returns explicit protocol error",
    )

    manager.exit(
        21
    )

    host.stop()


def test_preserves_preexisting_state():
    host = build_host()

    host.mark_unhealthy(
        "echo-2"
    )

    manager = RuntimeMaintenanceManager(
        host
    )

    manager.enter(
        30
    )

    manager.exit(
        31
    )

    first = (
        host.load_balancer
        .registry
        .get(
            "echo-1"
        )
    )

    second = (
        host.load_balancer
        .registry
        .get(
            "echo-2"
        )
    )

    eq(
        first.healthy,
        True,
        "healthy instance restored healthy",
    )

    eq(
        second.healthy,
        False,
        "pre-existing unhealthy state preserved",
    )

    host.stop()


def test_drain_waits_for_active_request():
    started = threading.Event()
    release = threading.Event()
    responses = []

    def slow(
        request,
    ):
        started.set()

        release.wait(
            3.0
        )

        return (
            ServiceResponse
            .success_response(
                request,
                data={
                    "done": True,
                },
            )
        )

    host = ServiceHost()

    host.add_service(
        "slow-1",
        "slow_service",
        slow,
    )

    host.start(
        1
    )

    manager = RuntimeMaintenanceManager(
        host
    )

    def run_request():
        responses.append(
            host.dispatch(
                ServiceRequest(
                    "slow-request",
                    "slow_service",
                    "run",
                )
            )
        )

    thread = threading.Thread(
        target=run_request
    )

    thread.start()

    check(
        started.wait(
            2.0
        ),
        "slow request starts",
    )

    status = manager.begin_draining(
        40,
        reason="shutdown",
    )

    eq(
        status[
            "mode"
        ],
        "draining",
        "active request keeps runtime in draining mode",
    )

    eq(
        status[
            "drain"
        ][
            "active_requests"
        ][
            "total"
        ],
        1,
        "active request counted during drain",
    )

    still = manager.advance(
        41
    )

    eq(
        still[
            "mode"
        ],
        "draining",
        "advance does not enter maintenance before drain completes",
    )

    rejected = host.dispatch(
        ServiceRequest(
            "new-request",
            "slow_service",
            "run",
        )
    )

    eq(
        rejected.success,
        False,
        "new service-host request cannot enter paused instance",
    )

    release.set()

    thread.join(
        timeout=3.0
    )

    eq(
        responses[
            0
        ].success,
        True,
        "in-flight request completes successfully",
    )

    entered = manager.advance(
        42
    )

    eq(
        entered[
            "mode"
        ],
        "maintenance",
        "drained runtime advances to maintenance",
    )

    manager.exit(
        43
    )

    host.stop()


def test_exit_during_active_drain_rejected():
    started = threading.Event()
    release = threading.Event()

    def slow(
        request,
    ):
        started.set()
        release.wait(
            3.0
        )

        return (
            ServiceResponse
            .success_response(
                request
            )
        )

    host = ServiceHost()

    host.add_service(
        "slow",
        "svc",
        slow,
    )

    host.start(
        1
    )

    thread = threading.Thread(
        target=lambda: host.dispatch(
            ServiceRequest(
                "r",
                "svc",
                "run",
            )
        )
    )

    thread.start()

    check(
        started.wait(
            2.0
        ),
        "active request started",
    )

    manager = RuntimeMaintenanceManager(
        host
    )

    manager.begin_draining(
        50
    )

    expect_error(
        RuntimeError,
        lambda: manager.exit(
            51
        ),
        "cannot exit draining while active request remains",
    )

    release.set()

    thread.join(
        timeout=3.0
    )

    manager.advance(
        52
    )

    manager.exit(
        53
    )

    host.stop()


def test_snapshot():
    host = build_host()

    host.disable(
        "echo-2"
    )

    drain = ServiceDrainManager(
        host
    )

    result = drain.begin(
        60
    )

    snapshot = result[
        "snapshot"
    ]

    eq(
        snapshot[
            "instances"
        ][
            "echo-1"
        ][
            "enabled"
        ],
        True,
        "snapshot captures enabled instance",
    )

    eq(
        snapshot[
            "instances"
        ][
            "echo-2"
        ][
            "enabled"
        ],
        False,
        "snapshot captures pre-disabled instance",
    )

    drain.restore()

    descriptor = (
        host.discovery
        .registry
        .get(
            "echo-2"
        )
    )

    eq(
        descriptor.enabled,
        False,
        "restore preserves pre-disabled instance",
    )

    host.stop()


def main():
    test_state()
    test_enter_maintenance_when_idle()
    test_dispatcher_codes()
    test_preserves_preexisting_state()
    test_drain_waits_for_active_request()
    test_exit_during_active_drain_rejected()
    test_snapshot()

    print(
        "RUNTIME MAINTENANCE TEST SUITE: PASS"
    )
    print(
        "Assertions passed:",
        ASSERTIONS,
    )
    print(
        "Files validated: 5/5"
    )
    print(
        "Normal/draining/maintenance state machine: VALIDATED"
    )
    print(
        "New-request traffic drain: VALIDATED"
    )
    print(
        "In-flight request completion: VALIDATED"
    )
    print(
        "Pre-maintenance service state restoration: VALIDATED"
    )
    print(
        "Explicit maintenance protocol errors: VALIDATED"
    )
    print(
        "Third-party dependencies: 0"
    )
    print(
        "Test-only concurrency dependencies: threading"
    )


main()
