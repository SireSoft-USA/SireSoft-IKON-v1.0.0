PARSERS_BASE = "libs/data/parsers/"
HOST_BASE = "runtime/service_host/"
CONFIG_BASE = "configs/services/"

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
        HOST_BASE,
        [
            "binding.py",
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
    "instance.py",
    "definition.py",
    "catalog.py",
    "codec.py",
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
            "service config implementation contains forbidden import: "
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


def test_instance():
    instance = ServiceInstanceConfig(
        "rag-1",
        endpoint="local://rag/rag-1",
        metadata={
            "zone": "local",
        },
    )

    eq(
        instance.instance_id,
        "rag-1",
        "instance config id",
    )

    eq(
        instance.to_dict()["metadata"]["zone"],
        "local",
        "instance metadata serialized",
    )


def test_definition():
    definition = ServiceDefinition(
        service_name="rag_service",
        instances=[
            ServiceInstanceConfig("rag-1"),
            ServiceInstanceConfig("rag-2"),
        ],
        lease_seconds=30,
        max_consecutive_failures=2,
    )

    eq(
        len(definition.instances),
        2,
        "service definition instance count",
    )

    eq(
        definition.lease_seconds,
        30,
        "service definition lease typed",
    )


def test_catalog():
    catalog = ServiceConfigCatalog()

    catalog.add(
        ServiceDefinition(
            "a",
            [
                ServiceInstanceConfig("a-1"),
            ],
        )
    )

    catalog.add(
        ServiceDefinition(
            "b",
            [
                ServiceInstanceConfig("b-1"),
                ServiceInstanceConfig("b-2"),
            ],
        )
    )

    eq(
        catalog.services(),
        [
            "a",
            "b",
        ],
        "catalog preserves insertion order",
    )

    eq(
        catalog.instance_count(),
        3,
        "catalog total instance count",
    )

    expect_error(
        ValueError,
        lambda: catalog.add(
            ServiceDefinition(
                "a",
                [
                    ServiceInstanceConfig("a-2"),
                ],
            )
        ),
        "duplicate logical service rejected",
    )


def test_codec():
    text = (
        '{"services":['
        '{"service_name":"rag_service",'
        '"lease_seconds":45,'
        '"max_consecutive_failures":4,'
        '"endpoint_template":"local://{service}/{instance}",'
        '"metadata":{"team":"ai"},'
        '"instances":['
        '{"instance_id":"rag-1","metadata":{"zone":"a"}},'
        '{"instance_id":"rag-2","endpoint":"local://custom/rag-2"}'
        ']}]}'
    )

    catalog = ServiceConfigCodec().decode_text(text)

    definition = catalog.get(
        "rag_service"
    )

    eq(
        definition.max_consecutive_failures,
        4,
        "codec maps failure threshold",
    )

    eq(
        definition.instances[0].metadata["zone"],
        "a",
        "codec maps instance metadata",
    )


def test_global_duplicate_instance_rejected():
    text = (
        '{"services":['
        '{"service_name":"one","instances":[{"instance_id":"shared"}]},'
        '{"service_name":"two","instances":[{"instance_id":"shared"}]}'
        ']}'
    )

    expect_error(
        ValueError,
        lambda: ServiceConfigCodec().decode_text(
            text
        ),
        "duplicate global instance id rejected",
    )


def test_binding_factory():
    text = (
        '{"services":['
        '{"service_name":"echo_service",'
        '"lease_seconds":15,'
        '"max_consecutive_failures":5,'
        '"endpoint_template":"local://{service}/{instance}",'
        '"metadata":{"tier":"core","zone":"default"},'
        '"instances":['
        '{"instance_id":"echo-1","metadata":{"zone":"west"}}'
        ']}]}'
    )

    catalog = ServiceConfigCodec().decode_text(
        text
    )

    def echo_handler(request):
        return request

    bindings = ServiceBindingFactory().build(
        catalog,
        lambda service_name, instance_id: (
            echo_handler
        ),
    )

    binding = bindings[0]

    eq(
        binding.instance_id,
        "echo-1",
        "binding factory instance id",
    )

    eq(
        binding.service_name,
        "echo_service",
        "binding factory service name",
    )

    eq(
        binding.endpoint,
        "local://echo_service/echo-1",
        "binding factory endpoint template expansion",
    )

    eq(
        binding.lease_seconds,
        15,
        "binding factory lease",
    )

    eq(
        binding.max_consecutive_failures,
        5,
        "binding factory failure threshold",
    )

    eq(
        binding.metadata["tier"],
        "core",
        "definition metadata inherited",
    )

    eq(
        binding.metadata["zone"],
        "west",
        "instance metadata overrides definition",
    )

    eq(
        binding.metadata[
            "configured_service_name"
        ],
        "echo_service",
        "binding carries config provenance",
    )


def test_invalid_handler_provider():
    catalog = ServiceConfigCatalog()

    catalog.add(
        ServiceDefinition(
            "svc",
            [
                ServiceInstanceConfig("svc-1"),
            ],
        )
    )

    expect_error(
        TypeError,
        lambda: ServiceBindingFactory().build(
            catalog,
            lambda service_name, instance_id: (
                "not-a-handler"
            ),
        ),
        "invalid provider handler rejected",
    )


def main():
    test_instance()
    test_definition()
    test_catalog()
    test_codec()
    test_global_duplicate_instance_rejected()
    test_binding_factory()
    test_invalid_handler_provider()

    print(
        "SERVICE CONFIG TEST SUITE: PASS"
    )
    print(
        "Assertions passed:",
        ASSERTIONS,
    )
    print(
        "Files validated: 5/5"
    )
    print(
        "Typed service/instance definitions: VALIDATED"
    )
    print(
        "Handwritten JSON decoding: VALIDATED"
    )
    print(
        "Global instance-id uniqueness: VALIDATED"
    )
    print(
        "Handler/config separation boundary: VALIDATED"
    )
    print(
        "ServiceBinding generation: VALIDATED"
    )
    print(
        "Endpoint-template expansion: VALIDATED"
    )
    print(
        "Metadata inheritance/override: VALIDATED"
    )
    print(
        "Third-party dependencies: 0"
    )


main()
