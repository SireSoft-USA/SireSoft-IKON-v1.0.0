PARSERS_BASE = "libs/data/parsers/"
METRICS_BASE = "services/metrics_service/"
CONFIG_BASE = "configs/metrics/"

namespace = {
    "__builtins__": __builtins__,
}

groups = [
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
    "metric.py",
    "config.py",
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
            "metrics config implementation contains forbidden import: "
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


def test_metric_config():
    metric = MetricConfig(
        name="requests_total",
        metric_type="counter",
        description="requests",
        label_names=[
            "service",
            "outcome",
        ],
    )

    eq(
        metric.metric_type,
        "counter",
        "metric type stored",
    )

    eq(
        metric.label_names,
        [
            "service",
            "outcome",
        ],
        "metric labels stored",
    )


def test_histogram_validation():
    metric = MetricConfig(
        name="latency_seconds",
        metric_type="histogram",
        unit="seconds",
        buckets=[
            0.1,
            0.5,
            1.0,
        ],
    )

    eq(
        metric.buckets,
        [
            0.1,
            0.5,
            1.0,
        ],
        "histogram buckets normalized",
    )

    expect_error(
        ValueError,
        lambda: MetricConfig(
            name="bad",
            metric_type="histogram",
            buckets=[
                1.0,
                0.5,
            ],
        ),
        "unsorted histogram buckets rejected",
    )


def test_codec():
    text = (
        '{"metrics":['
        '{"name":"requests_total","metric_type":"counter",'
        '"description":"requests","label_names":["service"]},'
        '{"name":"latency","metric_type":"histogram",'
        '"unit":"seconds","buckets":[0.1,0.5,1.0]},'
        '{"name":"disabled","metric_type":"gauge","enabled":false}'
        '],'
        '"persistence_path":"state/metrics.bin"}'
    )

    config = (
        MetricsConfigCodec()
        .decode_text(
            text
        )
    )

    eq(
        len(
            config.metrics
        ),
        3,
        "codec metric count",
    )

    eq(
        len(
            config.enabled_metrics()
        ),
        2,
        "codec enabled metric count",
    )

    eq(
        config.persistence_path,
        "state/metrics.bin",
        "codec persistence path",
    )


def test_duplicate_metric_rejected():
    expect_error(
        ValueError,
        lambda: MetricsConfig(
            metrics=[
                MetricConfig(
                    "same",
                    "counter",
                ),
                MetricConfig(
                    "same",
                    "gauge",
                ),
            ],
        ),
        "duplicate metric name rejected",
    )


def test_validator():
    labels = [
        "a",
        "b",
        "c",
        "d",
        "e",
        "f",
        "g",
        "h",
        "i",
    ]

    config = MetricsConfig(
        metrics=[
            MetricConfig(
                "wide",
                "gauge",
                label_names=labels,
            ),
        ],
    )

    result = (
        MetricsConfigValidator()
        .validate(
            config
        )
    )

    eq(
        result[
            "valid"
        ],
        True,
        "wide metric remains valid",
    )

    warning_codes = [
        item[
            "code"
        ]
        for item
        in result[
            "warnings"
        ]
    ]

    check(
        "HIGH_LABEL_CARDINALITY_RISK"
        in warning_codes,
        "label cardinality risk warned",
    )


def test_no_enabled_metrics_invalid():
    config = MetricsConfig(
        metrics=[
            MetricConfig(
                "off",
                "counter",
                enabled=False,
            ),
        ],
    )

    result = (
        MetricsConfigValidator()
        .validate(
            config
        )
    )

    eq(
        result[
            "valid"
        ],
        False,
        "no-enabled-metric config invalid",
    )

    eq(
        result[
            "errors"
        ][
            0
        ][
            "code"
        ],
        "NO_ENABLED_METRICS",
        "no enabled metric error code",
    )


def test_factory_manager():
    config = MetricsConfig(
        metrics=[
            MetricConfig(
                "requests_total",
                "counter",
                label_names=[
                    "service",
                ],
            ),
            MetricConfig(
                "active_requests",
                "gauge",
                label_names=[
                    "service",
                ],
            ),
            MetricConfig(
                "request_duration",
                "histogram",
                unit="seconds",
                label_names=[
                    "service",
                ],
                buckets=[
                    0.1,
                    0.5,
                    1.0,
                ],
            ),
            MetricConfig(
                "off",
                "counter",
                enabled=False,
            ),
        ],
    )

    manager = (
        MetricsConfigFactory()
        .build_manager(
            config
        )
    )

    eq(
        manager.status()[
            "metric_count"
        ],
        3,
        "factory defines enabled metrics only",
    )

    manager.increment(
        "requests_total",
        timestamp=1,
        labels={
            "service": "rag",
        },
    )

    manager.set_gauge(
        "active_requests",
        2,
        timestamp=2,
        labels={
            "service": "rag",
        },
    )

    manager.observe(
        "request_duration",
        0.4,
        timestamp=3,
        labels={
            "service": "rag",
        },
    )

    requests = manager.get_metric(
        "requests_total"
    )

    eq(
        requests[
            "series"
        ][
            0
        ][
            "value"
        ],
        1.0,
        "configured counter updates",
    )

    active = manager.get_metric(
        "active_requests"
    )

    eq(
        active[
            "series"
        ][
            0
        ][
            "value"
        ],
        2.0,
        "configured gauge updates",
    )

    duration = manager.get_metric(
        "request_duration"
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
        "configured histogram observes sample",
    )

    eq(
        duration[
            "series"
        ][
            0
        ][
            "buckets"
        ][
            1
        ][
            "count"
        ],
        1,
        "configured histogram bucket count",
    )


def test_initialize_without_persistence():
    config = MetricsConfig(
        metrics=[
            MetricConfig(
                "only",
                "counter",
            ),
        ],
    )

    manager = (
        MetricsConfigFactory()
        .initialize(
            config,
            load_persisted=False,
        )
    )

    check(
        isinstance(
            manager,
            MetricsManager,
        ),
        "initialize returns MetricsManager",
    )

    eq(
        manager.status()[
            "metric_count"
        ],
        1,
        "initialize configures manager",
    )


def test_default_histogram_buckets():
    metric = MetricConfig(
        "latency",
        "histogram",
    )

    check(
        len(
            metric.buckets
        ) > 0,
        "histogram receives default buckets",
    )


def main():
    test_metric_config()
    test_histogram_validation()
    test_codec()
    test_duplicate_metric_rejected()
    test_validator()
    test_no_enabled_metrics_invalid()
    test_factory_manager()
    test_initialize_without_persistence()
    test_default_histogram_buckets()

    print(
        "METRICS CONFIG TEST SUITE: PASS"
    )
    print(
        "Assertions passed:",
        ASSERTIONS,
    )
    print(
        "Files validated: 5/5"
    )
    print(
        "Typed counter/gauge/histogram configuration: VALIDATED"
    )
    print(
        "Handwritten JSON decoding: VALIDATED"
    )
    print(
        "Histogram bucket validation: VALIDATED"
    )
    print(
        "Metric cardinality warnings: VALIDATED"
    )
    print(
        "MetricsManager generation: VALIDATED"
    )
    print(
        "Configured counter/gauge/histogram updates: VALIDATED"
    )
    print(
        "Persistence initialization boundary: VALIDATED"
    )
    print(
        "Third-party dependencies: 0"
    )


main()
