import os
import shutil

PROTOCOL_BASE = "libs/protocol/"
LOAD_BALANCER_BASE = "services/load_balancer/"
DISCOVERY_BASE = "services/service_discovery/"
LOGGING_BASE = "services/logging_service/"
METRICS_BASE = "services/metrics_service/"
TRACING_BASE = "services/tracing_service/"
CONCURRENCY_BASE = "runtime/concurrency/"
PROCESSES_BASE = "runtime/processes/"
STORAGE_BASE = "runtime/storage/"
LIFECYCLE_BASE = "runtime/lifecycle/"
BOOTSTRAP_BASE = "runtime/bootstrap/"
HOST_BASE = "runtime/service_host/"
HEALTH_BASE = "runtime/health/"
SIGNALS_BASE = "runtime/signals/"
OBSERVABILITY_BASE = "runtime/observability/"
DIAGNOSTICS_BASE = "runtime/diagnostics/"
RECOVERY_BASE = "runtime/recovery/"
MAINTENANCE_BASE = "runtime/maintenance/"
CONTROL_BASE = "runtime/control_plane/"
COMPOSITION_BASE = "runtime/composition/"
ENTRYPOINT_BASE = "runtime/entrypoint/"
CLI_BASE = "runtime/cli/"

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
        LOGGING_BASE,
        [
            "record.py",
            "sanitizer.py",
            "sink.py",
            "archive.py",
            "manager.py",
        ],
    ),
    (
        METRICS_BASE,
        [
            "labels.py",
            "metric.py",
            "registry.py",
            "persistence.py",
            "manager.py",
        ],
    ),
    (
        TRACING_BASE,
        [
            "span.py",
            "trace.py",
            "sampler.py",
            "persistence.py",
            "manager.py",
        ],
    ),
    (
        CONCURRENCY_BASE,
        [
            "future.py",
            "task_queue.py",
            "semaphore.py",
            "worker_pool.py",
            "service_executor.py",
            "network_runner.py",
        ],
    ),
    (
        PROCESSES_BASE,
        [
            "spec.py",
            "process.py",
            "registry.py",
            "supervisor.py",
            "group.py",
        ],
    ),
    (
        STORAGE_BASE,
        [
            "path_policy.py",
            "atomic_file.py",
            "namespace.py",
            "store.py",
        ],
    ),
    (
        LIFECYCLE_BASE,
        [
            "resource.py",
            "graph.py",
            "manager.py",
            "adapters.py",
        ],
    ),
    (
        BOOTSTRAP_BASE,
        [
            "config.py",
            "context.py",
            "application.py",
            "builder.py",
        ],
    ),
    (
        HOST_BASE,
        [
            "binding.py",
            "registry.py",
            "host.py",
            "gateway_dispatcher.py",
            "lifecycle_adapter.py",
        ],
    ),
    (
        HEALTH_BASE,
        [
            "probe.py",
            "adapters.py",
            "manager.py",
            "monitoring_bridge.py",
        ],
    ),
    (
        SIGNALS_BASE,
        [
            "event.py",
            "coordinator.py",
            "registry.py",
            "handler.py",
            "runtime_bridge.py",
            "lifecycle_adapter.py",
        ],
    ),
    (
        OBSERVABILITY_BASE,
        [
            "context.py",
            "manager.py",
            "dispatcher.py",
            "snapshot.py",
        ],
    ),
    (
        DIAGNOSTICS_BASE,
        [
            "redactor.py",
            "finding.py",
            "analyzer.py",
            "report.py",
            "collector.py",
        ],
    ),
    (
        RECOVERY_BASE,
        [
            "action.py",
            "plan.py",
            "policy.py",
            "executor.py",
            "adapters.py",
            "manager.py",
        ],
    ),
    (
        MAINTENANCE_BASE,
        [
            "state.py",
            "snapshot.py",
            "drain.py",
            "manager.py",
            "dispatcher.py",
        ],
    ),
    (
        CONTROL_BASE,
        [
            "result.py",
            "controller.py",
            "service.py",
        ],
    ),
    (
        COMPOSITION_BASE,
        [
            "spec.py",
            "components.py",
            "builder.py",
            "system.py",
        ],
    ),
    (
        ENTRYPOINT_BASE,
        [
            "exit_status.py",
            "runner.py",
            "factory.py",
            "main.py",
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
    "command.py",
    "parser.py",
    "config.py",
    "application.py",
]:
    path = CLI_BASE + filename

    source = open(
        path,
        "r",
        encoding="utf-8",
    ).read()

    if "import " in source:
        raise AssertionError(
            "runtime CLI implementation contains forbidden import: "
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

ROOT = (
    "runtime/cli/"
    "_test_runtime"
)


class Clock:
    def __init__(
        self,
        start=100,
    ):
        self.value = start

    def now(
        self,
    ):
        value = self.value
        self.value += 1
        return value


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


def cleanup():
    if os.path.exists(
        ROOT
    ):
        shutil.rmtree(
            ROOT
        )


def echo(
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


def test_parser():
    parser = RuntimeCLIParser()

    command = parser.parse([
        "run",
        "--storage-root",
        ROOT,
        "--workers",
        "2",
        "--queue-capacity",
        "8",
        "--namespace",
        "runtime",
        "--namespace",
        "cache",
        "--enable-signals",
        "--wait-timeout",
        "0.01",
    ])

    eq(
        command.name,
        "run",
        "CLI parser command",
    )

    eq(
        command.option(
            "workers"
        ),
        "2",
        "CLI parser value option",
    )

    eq(
        command.option(
            "namespace"
        ),
        [
            "runtime",
            "cache",
        ],
        "CLI parser repeated namespace",
    )

    eq(
        command.option(
            "enable-signals"
        ),
        True,
        "CLI parser boolean option",
    )


def test_parser_errors():
    parser = RuntimeCLIParser()

    expect_error(
        ValueError,
        lambda: parser.parse([]),
        "missing command rejected",
    )

    expect_error(
        ValueError,
        lambda: parser.parse([
            "unknown",
        ]),
        "unknown command rejected",
    )

    expect_error(
        ValueError,
        lambda: parser.parse([
            "run",
            "--workers",
        ]),
        "missing option value rejected",
    )

    expect_error(
        ValueError,
        lambda: parser.parse([
            "run",
            "--wat",
            "1",
        ]),
        "unknown option rejected",
    )


def test_config():
    parser = RuntimeCLIParser()

    command = parser.parse([
        "validate",
        "--storage-root",
        ROOT,
        "--workers",
        "3",
        "--queue-capacity",
        "9",
        "--wait-timeout",
        "2.5",
    ])

    config = RuntimeCLIConfig.from_command(
        command
    )

    eq(
        config.worker_count,
        3,
        "CLI config workers typed",
    )

    eq(
        config.queue_capacity,
        9,
        "CLI config queue capacity typed",
    )

    eq(
        config.wait_timeout,
        2.5,
        "CLI config timeout typed",
    )


def test_validate_command():
    cleanup()

    app = RuntimeCLIApplication(
        time_provider=(
            Clock().now
        ),
        binding_provider=(
            lambda: [
                ServiceBinding(
                    "echo-1",
                    "echo_service",
                    echo,
                ),
            ]
        ),
    )

    result = app.execute([
        "validate",
        "--storage-root",
        ROOT,
        "--workers",
        "1",
        "--queue-capacity",
        "4",
    ])

    eq(
        result[
            "ok"
        ],
        True,
        "validate command succeeds",
    )

    eq(
        result[
            "command"
        ],
        "validate",
        "validate command label",
    )

    eq(
        result[
            "components"
        ][
            "sealed"
        ],
        True,
        "validate builds sealed runtime composition",
    )


def test_run_timeout():
    cleanup()

    app = RuntimeCLIApplication(
        time_provider=(
            Clock().now
        ),
        binding_provider=(
            lambda: [
                ServiceBinding(
                    "echo-1",
                    "echo_service",
                    echo,
                ),
            ]
        ),
    )

    result = app.execute([
        "run",
        "--storage-root",
        ROOT,
        "--workers",
        "1",
        "--queue-capacity",
        "4",
        "--wait-timeout",
        "0.01",
    ])

    eq(
        result[
            "code"
        ],
        RuntimeExitStatus
        .EXIT_WAIT_TIMEOUT,
        "CLI run propagates runtime wait-timeout exit code",
    )

    eq(
        result[
            "runtime"
        ][
            "stopped"
        ],
        True,
        "CLI run timeout still shuts runtime down",
    )


def test_invalid_config_returns_cli_error():
    app = RuntimeCLIApplication(
        time_provider=(
            Clock().now
        )
    )

    result = app.execute([
        "validate",
        "--workers",
        "0",
    ])

    eq(
        result[
            "ok"
        ],
        False,
        "invalid CLI config returns error",
    )

    eq(
        result[
            "code"
        ],
        2,
        "invalid CLI config uses CLI error code",
    )


def test_positionals_rejected():
    app = RuntimeCLIApplication(
        time_provider=(
            Clock().now
        )
    )

    result = app.execute([
        "validate",
        "unexpected",
    ])

    eq(
        result[
            "ok"
        ],
        False,
        "unexpected positional argument rejected",
    )


def test_binding_provider_validation():
    app = RuntimeCLIApplication(
        time_provider=(
            Clock().now
        ),
        binding_provider=(
            lambda: "bad"
        ),
    )

    result = app.execute([
        "validate",
        "--storage-root",
        ROOT,
    ])

    eq(
        result[
            "ok"
        ],
        False,
        "invalid binding provider result rejected",
    )


def test_command_counter():
    app = RuntimeCLIApplication(
        time_provider=(
            Clock().now
        )
    )

    app.execute([
        "validate",
        "--workers",
        "0",
    ])

    app.execute([
        "wat",
    ])

    eq(
        app.status()[
            "total_commands"
        ],
        2,
        "CLI command counter",
    )


def main():
    try:
        test_parser()
        test_parser_errors()
        test_config()
        test_validate_command()
        test_run_timeout()
        test_invalid_config_returns_cli_error()
        test_positionals_rejected()
        test_binding_provider_validation()
        test_command_counter()

    finally:
        cleanup()

    print(
        "RUNTIME CLI TEST SUITE: PASS"
    )
    print(
        "Assertions passed:",
        ASSERTIONS,
    )
    print(
        "Files validated: 4/4"
    )
    print(
        "Handwritten command-line parsing: VALIDATED"
    )
    print(
        "Typed runtime launch configuration: VALIDATED"
    )
    print(
        "Composition validation command: VALIDATED"
    )
    print(
        "Entrypoint run command integration: VALIDATED"
    )
    print(
        "Runtime exit-code propagation: VALIDATED"
    )
    print(
        "Binding-provider composition boundary: VALIDATED"
    )
    print(
        "Third-party dependencies: 0"
    )


main()
