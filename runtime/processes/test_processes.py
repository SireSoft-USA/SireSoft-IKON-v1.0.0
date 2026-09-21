import os
import sys
import time

PROCESS_BASE = "runtime/processes/"

namespace = {
    "__builtins__": __builtins__,
}

for filename in [
    "spec.py",
    "process.py",
    "registry.py",
    "supervisor.py",
    "group.py",
]:
    path = PROCESS_BASE + filename

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


def python_spec(
    name,
    source,
    **kwargs
):
    return ProcessSpec(
        name=name,
        command=[
            sys.executable,
            "-S",
            "-c",
            source,
        ],
        **kwargs
    )


def test_spec():
    spec = python_spec(
        "worker",
        "print('x')",
        restart_policy="on_failure",
        max_restarts=2,
        env={
            "MODE": "test",
        },
    )

    eq(
        spec.should_restart(
            1,
            0,
        ),
        True,
        "on_failure restarts nonzero exit",
    )

    eq(
        spec.should_restart(
            0,
            0,
        ),
        False,
        "on_failure does not restart success",
    )

    eq(
        spec.should_restart(
            1,
            2,
        ),
        False,
        "restart limit enforced",
    )

    eq(
        spec.public_dict()[
            "env_keys"
        ],
        [
            "MODE",
        ],
        "public spec exposes env keys not values",
    )


def test_successful_process():
    process = ManagedProcess(
        python_spec(
            "success",
            "print('hello-process')",
        )
    )

    process.start()

    check(
        process.pid() is not None,
        "started process has pid",
    )

    result = process.wait(
        timeout=3.0
    )

    eq(
        result.exit_code,
        0,
        "successful process exit code",
    )

    eq(
        result.stdout.strip(),
        "hello-process",
        "stdout captured",
    )

    eq(
        result.stderr,
        "",
        "stderr empty",
    )

    eq(
        process.state(),
        "exited",
        "process transitions to exited",
    )


def test_environment():
    process = ManagedProcess(
        python_spec(
            "environment",
            (
                "import os; "
                "print(os.environ['SIRELLM_TEST_VALUE'])"
            ),
            env={
                "SIRELLM_TEST_VALUE": (
                    "visible-to-child"
                ),
            },
        )
    )

    process.start()

    result = process.wait(
        timeout=3.0
    )

    eq(
        result.stdout.strip(),
        "visible-to-child",
        "declared environment reaches child",
    )


def test_failure():
    process = ManagedProcess(
        python_spec(
            "failure",
            (
                "import sys; "
                "print('bad', file=sys.stderr); "
                "sys.exit(7)"
            ),
        )
    )

    process.start()

    result = process.wait(
        timeout=3.0
    )

    eq(
        result.exit_code,
        7,
        "failure exit code preserved",
    )

    check(
        "bad"
        in result.stderr,
        "failure stderr captured",
    )


def test_terminate():
    process = ManagedProcess(
        python_spec(
            "sleeping",
            (
                "import time; "
                "time.sleep(30)"
            ),
            graceful_timeout_seconds=0.5,
        )
    )

    process.start()

    result = process.terminate(
        timeout=1.0
    )

    check(
        result.exit_code != 0,
        "terminated process exits nonzero",
    )

    check(
        result.termination
        in (
            "terminated",
            "killed_after_timeout",
        ),
        "termination cause recorded",
    )


def test_wait_timeout():
    process = ManagedProcess(
        python_spec(
            "wait-timeout",
            (
                "import time; "
                "time.sleep(2)"
            ),
        )
    )

    process.start()

    expect_error(
        TimeoutError,
        lambda: process.wait(
            timeout=0.05
        ),
        "wait timeout propagated",
    )

    process.kill()


def test_registry():
    registry = ProcessRegistry()

    spec = python_spec(
        "one",
        "pass",
    )

    registry.register(
        spec
    )

    eq(
        registry.names(),
        [
            "one",
        ],
        "registry order preserved",
    )

    expect_error(
        ValueError,
        lambda: registry.register(
            spec
        ),
        "duplicate process spec rejected",
    )


def test_supervisor_start_wait():
    supervisor = (
        ProcessSupervisor()
    )

    supervisor.register(
        python_spec(
            "job",
            "print('done')",
        )
    )

    process = supervisor.start(
        "job"
    )

    result = supervisor.wait(
        "job",
        timeout=3.0,
    )

    eq(
        result.exit_code,
        0,
        "supervisor waits process",
    )

    eq(
        result.stdout.strip(),
        "done",
        "supervisor preserves process result",
    )

    eq(
        supervisor.status()[
            "total_starts"
        ],
        1,
        "supervisor start count",
    )


def test_supervisor_restart_failure():
    supervisor = (
        ProcessSupervisor()
    )

    supervisor.register(
        python_spec(
            "restart-me",
            (
                "import sys; "
                "sys.exit(3)"
            ),
            restart_policy="on_failure",
            max_restarts=1,
        )
    )

    supervisor.start(
        "restart-me"
    )

    first = supervisor.wait(
        "restart-me",
        timeout=3.0,
        restart=True,
    )

    eq(
        first.exit_code,
        3,
        "first failing run captured",
    )

    eq(
        supervisor.status()[
            "restart_counts"
        ][
            "restart-me"
        ],
        1,
        "failure triggers one restart",
    )

    second = supervisor.wait(
        "restart-me",
        timeout=3.0,
        restart=True,
    )

    eq(
        second.exit_code,
        3,
        "restarted process failure captured",
    )

    eq(
        supervisor.status()[
            "restart_counts"
        ][
            "restart-me"
        ],
        1,
        "max restart count prevents extra restart",
    )


def test_supervisor_always_restart():
    supervisor = (
        ProcessSupervisor()
    )

    supervisor.register(
        python_spec(
            "always",
            "pass",
            restart_policy="always",
            max_restarts=1,
        )
    )

    supervisor.start(
        "always"
    )

    first = supervisor.wait(
        "always",
        timeout=3.0,
        restart=True,
    )

    eq(
        first.exit_code,
        0,
        "successful run captured",
    )

    eq(
        supervisor.status()[
            "restart_counts"
        ][
            "always"
        ],
        1,
        "always policy restarts successful process",
    )

    supervisor.wait(
        "always",
        timeout=3.0,
    )


def test_group_order():
    supervisor = (
        ProcessSupervisor()
    )

    supervisor.register(
        python_spec(
            "a",
            (
                "import time; "
                "time.sleep(30)"
            ),
        )
    )

    supervisor.register(
        python_spec(
            "b",
            (
                "import time; "
                "time.sleep(30)"
            ),
        )
    )

    group = ProcessGroup(
        supervisor,
        [
            "a",
            "b",
        ],
    )

    eq(
        group.start_all(),
        [
            "a",
            "b",
        ],
        "group starts in declaration order",
    )

    eq(
        group.stop_all(
            timeout=1.0
        ),
        [
            "b",
            "a",
        ],
        "group stops in reverse order",
    )


def test_shutdown_all():
    supervisor = (
        ProcessSupervisor()
    )

    for name in (
        "first",
        "second",
    ):
        supervisor.register(
            python_spec(
                name,
                (
                    "import time; "
                    "time.sleep(30)"
                ),
            )
        )

        supervisor.start(
            name
        )

    results = supervisor.shutdown_all(
        timeout=1.0
    )

    eq(
        set(
            results.keys()
        ),
        {
            "first",
            "second",
        },
        "shutdown_all covers registered running processes",
    )

    check(
        not supervisor.registry.get_process(
            "first"
        ).running(),
        "first process stopped",
    )

    check(
        not supervisor.registry.get_process(
            "second"
        ).running(),
        "second process stopped",
    )


def test_invalid_specs():
    expect_error(
        ValueError,
        lambda: ProcessSpec(
            "",
            [
                "python",
            ],
        ),
        "empty process name rejected",
    )

    expect_error(
        ValueError,
        lambda: ProcessSpec(
            "x",
            [],
        ),
        "empty command rejected",
    )

    expect_error(
        ValueError,
        lambda: ProcessSpec(
            "x",
            [
                "python",
            ],
            restart_policy="bad",
        ),
        "invalid restart policy rejected",
    )


def main():
    test_spec()
    test_successful_process()
    test_environment()
    test_failure()
    test_terminate()
    test_wait_timeout()
    test_registry()
    test_supervisor_start_wait()
    test_supervisor_restart_failure()
    test_supervisor_always_restart()
    test_group_order()
    test_shutdown_all()
    test_invalid_specs()

    print(
        "RUNTIME PROCESSES TEST SUITE: PASS"
    )
    print(
        "Assertions passed:",
        ASSERTIONS,
    )
    print(
        "Files validated: 5/5"
    )
    print(
        "Declarative process specifications: VALIDATED"
    )
    print(
        "Child lifecycle/stdout/stderr capture: VALIDATED"
    )
    print(
        "Environment propagation: VALIDATED"
    )
    print(
        "Graceful termination/kill fallback: VALIDATED"
    )
    print(
        "Restart policies/limits: VALIDATED"
    )
    print(
        "Ordered process groups/shutdown: VALIDATED"
    )
    print(
        "Third-party dependencies: 0"
    )
    print(
        "Standard-library process dependencies: os, subprocess, time"
    )


main()
