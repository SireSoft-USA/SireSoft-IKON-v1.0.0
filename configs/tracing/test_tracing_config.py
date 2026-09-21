SERIAL_BASE = "libs/core/serialization/"
PARSERS_BASE = "libs/data/parsers/"
METRICS_BASE = "services/metrics_service/"
TRACING_BASE = "services/tracing_service/"
CONFIG_BASE = "configs/tracing/"

namespace = {
    "__builtins__": __builtins__,
}

groups = [
    (
        SERIAL_BASE,
        [
            "checksum.py",
            "binary_writer.py",
            "binary_reader.py",
        ],
    ),
    (
        PARSERS_BASE,
        [
            "json_parser.py",
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
            "sampler.py",
            "span.py",
            "trace.py",
            "persistence.py",
            "manager.py",
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
    "sampler.py",
    "config.py",
    "codec.py",
    "validator.py",
    "factory.py",
]:
    path = (
        CONFIG_BASE
        + filename
    )

    source = open(
        path,
        "r",
        encoding="utf-8",
    ).read()

    if "import " in source:
        raise AssertionError(
            "tracing config implementation contains forbidden import: "
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
        + repr(
            actual
        )
        + " expected="
        + repr(
            expected
        ),
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


def test_sampler_config():
    sampler = TraceSamplerConfig(
        1,
        4,
    )

    eq(
        sampler.to_dict(),
        {
            "numerator": 1,
            "denominator": 4,
        },
        "sampler config serializes",
    )

    expect_error(
        ValueError,
        lambda: TraceSamplerConfig(
            5,
            4,
        ),
        "invalid sampler ratio rejected",
    )


def test_codec():
    text = (
        '{"sampler":{"numerator":1,"denominator":10},'
        '"persistence_path":"state/traces.bin",'
        '"attach_metrics":false,'
        '"publish_events":false,'
        '"metadata":{"environment":"test"}}'
    )

    config = (
        TracingConfigCodec()
        .decode_text(
            text
        )
    )

    eq(
        config.sampler.numerator,
        1,
        "codec sampler numerator",
    )

    eq(
        config.sampler.denominator,
        10,
        "codec sampler denominator",
    )

    eq(
        config.persistence_path,
        "state/traces.bin",
        "codec persistence path",
    )

    eq(
        config.attach_metrics,
        False,
        "codec metrics attachment flag",
    )


def test_validator():
    disabled = TracingConfig(
        sampler=(
            TraceSamplerConfig(
                0,
                1,
            )
        ),
        attach_metrics=False,
    )

    result = (
        TracingConfigValidator()
        .validate(
            disabled
        )
    )

    codes = [
        item[
            "code"
        ]
        for item
        in result[
            "warnings"
        ]
    ]

    check(
        "TRACING_DISABLED_BY_SAMPLER"
        in codes,
        "zero sampling warns",
    )

    eq(
        result[
            "sample_ratio"
        ],
        0.0,
        "zero sampling ratio",
    )


def test_factory_without_metrics():
    config = TracingConfig(
        sampler=(
            TraceSamplerConfig(
                1,
                1,
            )
        ),
        attach_metrics=False,
        publish_events=False,
    )

    manager = (
        TracingConfigFactory()
        .build_manager(
            config
        )
    )

    eq(
        manager.status()[
            "sampler"
        ],
        {
            "numerator": 1,
            "denominator": 1,
        },
        "factory applies sampler",
    )

    start = manager.start_span(
        trace_id="trace-1",
        name="request",
        service_name=(
            "rag_service"
        ),
        start_time=10,
        operation="answer",
    )

    eq(
        start[
            "sampled"
        ],
        True,
        "full-sampling config records span",
    )

    span_id = start[
        "span"
    ][
        "span_id"
    ]

    finish = manager.finish_span(
        trace_id="trace-1",
        span_id=span_id,
        end_time=15,
    )

    eq(
        finish[
            "span"
        ][
            "duration"
        ],
        5,
        "configured tracing manager finishes span",
    )

    eq(
        manager.status()[
            "total_finished"
        ],
        1,
        "configured tracing manager records finish count",
    )


def test_zero_sampler_drops():
    config = TracingConfig(
        sampler=(
            TraceSamplerConfig(
                0,
                1,
            )
        ),
        attach_metrics=False,
    )

    manager = (
        TracingConfigFactory()
        .build_manager(
            config
        )
    )

    result = manager.start_span(
        trace_id="drop-me",
        name="request",
        service_name="svc",
        start_time=1,
    )

    eq(
        result[
            "sampled"
        ],
        False,
        "zero sampler drops trace",
    )

    eq(
        manager.status()[
            "total_dropped"
        ],
        1,
        "dropped trace counted",
    )


def test_metrics_attachment():
    config = TracingConfig(
        sampler=(
            TraceSamplerConfig(
                1,
                1,
            )
        ),
        attach_metrics=True,
    )

    metrics = MetricsManager()

    manager = (
        TracingConfigFactory()
        .build_manager(
            config,
            metrics_manager=(
                metrics
            ),
        )
    )

    eq(
        manager.status()[
            "metrics_attached"
        ],
        True,
        "metrics attached to tracing manager",
    )

    start = manager.start_span(
        trace_id="metric-trace",
        name="request",
        service_name="svc",
        start_time=20,
        operation="run",
    )

    manager.finish_span(
        trace_id="metric-trace",
        span_id=start[
            "span"
        ][
            "span_id"
        ],
        end_time=22,
    )

    started = metrics.get_metric(
        "trace_spans_started_total"
    )

    eq(
        started[
            "series"
        ][
            0
        ][
            "value"
        ],
        1.0,
        "tracing config enables started-span metric",
    )

    duration = metrics.get_metric(
        "trace_span_duration_seconds"
    )

    eq(
        duration[
            "series"
        ][
            0
        ][
            "count"
        ],
        1,
        "tracing config enables duration histogram",
    )


def test_required_dependencies():
    needs_metrics = TracingConfig(
        attach_metrics=True,
    )

    expect_error(
        ValueError,
        lambda: (
            TracingConfigFactory()
            .build_manager(
                needs_metrics
            )
        ),
        "metrics dependency required when configured",
    )

    needs_events = TracingConfig(
        attach_metrics=False,
        publish_events=True,
    )

    expect_error(
        ValueError,
        lambda: (
            TracingConfigFactory()
            .build_manager(
                needs_events
            )
        ),
        "event bus dependency required when configured",
    )


def test_default_config():
    config = TracingConfig(
        attach_metrics=False,
    )

    eq(
        config.sampler.numerator,
        1,
        "default sampler numerator",
    )

    eq(
        config.sampler.denominator,
        1,
        "default sampler denominator",
    )


def main():
    test_sampler_config()
    test_codec()
    test_validator()
    test_factory_without_metrics()
    test_zero_sampler_drops()
    test_metrics_attachment()
    test_required_dependencies()
    test_default_config()

    print(
        "TRACING CONFIG TEST SUITE: PASS"
    )
    print(
        "Assertions passed:",
        ASSERTIONS,
    )
    print(
        "Files validated: 5/5"
    )
    print(
        "Typed deterministic sampling configuration: VALIDATED"
    )
    print(
        "Handwritten JSON decoding: VALIDATED"
    )
    print(
        "Sampling-ratio validation: VALIDATED"
    )
    print(
        "TracingManager generation: VALIDATED"
    )
    print(
        "Sample/drop behavior: VALIDATED"
    )
    print(
        "Metrics integration: VALIDATED"
    )
    print(
        "Dependency injection boundaries: VALIDATED"
    )
    print(
        "Third-party dependencies: 0"
    )


main()
