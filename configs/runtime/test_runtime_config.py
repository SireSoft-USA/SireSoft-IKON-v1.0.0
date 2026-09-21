import os
import shutil

PARSERS_BASE = "libs/data/parsers/"
HOST_BASE = "runtime/service_host/"
COMPOSITION_BASE = "runtime/composition/"
SERVER_BASE = "runtime/server/"
DAEMON_BASE = "runtime/daemon/"
CONFIG_BASE = "configs/runtime/"

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
    (
        COMPOSITION_BASE,
        [
            "spec.py",
        ],
    ),
    (
        SERVER_BASE,
        [
            "config.py",
        ],
    ),
    (
        DAEMON_BASE,
        [
            "config.py",
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
    "profile.py",
    "codec.py",
    "loader.py",
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
    "configs/runtime/"
    "_test_profiles"
)


class Clock:
    def __init__(
        self,
        start=10,
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


def test_profile():
    profile = RuntimeProfile(
        name="local",
        storage_root="runtime-data",
        worker_count=2,
        queue_capacity=8,
        storage_namespaces=[
            "runtime",
            "cache",
            "runtime",
        ],
        enable_signals=False,
        host="127.0.0.1",
        port=9000,
        max_requests=10,
    )

    eq(
        profile.storage_namespaces,
        [
            "runtime",
            "cache",
        ],
        "profile deduplicates namespaces",
    )

    eq(
        profile.port,
        9000,
        "profile stores port",
    )

    eq(
        profile.max_requests,
        10,
        "profile stores daemon limit",
    )


def test_codec_roundtrip():
    codec = RuntimeProfileCodec()

    profile = RuntimeProfile(
        name="dev",
        storage_root="data/dev",
        worker_count=3,
        queue_capacity=12,
        enable_signals=False,
        host="127.0.0.1",
        port=0,
        metadata={
            "note": (
                "local\nprofile"
            ),
        },
    )

    text = codec.encode_text(
        profile
    )

    decoded = codec.decode_text(
        text
    )

    eq(
        decoded.to_dict(),
        profile.to_dict(),
        "runtime profile JSON roundtrip",
    )


def test_loader():
    cleanup()

    os.makedirs(
        ROOT,
        exist_ok=True,
    )

    codec = RuntimeProfileCodec()

    profile = RuntimeProfile(
        name="test",
        storage_root="data/test",
        enable_signals=False,
    )

    path = os.path.join(
        ROOT,
        "test.json",
    )

    with open(
        path,
        "w",
        encoding="utf-8",
    ) as handle:
        handle.write(
            codec.encode_text(
                profile
            )
        )

    loader = RuntimeProfileLoader(
        ROOT,
        codec=codec,
    )

    eq(
        loader.exists(
            "test"
        ),
        True,
        "runtime profile loader sees profile",
    )

    loaded = loader.load(
        "test"
    )

    eq(
        loaded.name,
        "test",
        "runtime profile loader reads expected profile",
    )

    expect_error(
        ValueError,
        lambda: loader.path_for(
            "../escape"
        ),
        "runtime profile traversal rejected",
    )


def test_filename_profile_match():
    cleanup()

    os.makedirs(
        ROOT,
        exist_ok=True,
    )

    codec = RuntimeProfileCodec()

    wrong = RuntimeProfile(
        name="inside",
        storage_root="data",
    )

    with open(
        os.path.join(
            ROOT,
            "outside.json",
        ),
        "w",
        encoding="utf-8",
    ) as handle:
        handle.write(
            codec.encode_text(
                wrong
            )
        )

    loader = RuntimeProfileLoader(
        ROOT
    )

    expect_error(
        ValueError,
        lambda: loader.load(
            "outside"
        ),
        "profile filename/name mismatch rejected",
    )


def test_factory_integration():
    profile = RuntimeProfile(
        name="production",
        storage_root="runtime/prod",
        worker_count=6,
        queue_capacity=256,
        storage_namespaces=[
            "runtime",
            "models",
        ],
        enable_signals=True,
        host="0.0.0.0",
        port=8080,
        backlog=128,
        timeout_seconds=7.5,
        recv_chunk_bytes=8192,
        max_idle_timeouts=50,
        metadata={
            "environment": "prod",
        },
    )

    factory = RuntimeProfileFactory()

    binding = ServiceBinding(
        "svc-1",
        "svc",
        lambda request: None,
    )

    system_spec = (
        factory
        .build_system_spec(
            profile,
            Clock().now,
            service_bindings=[
                binding,
            ],
        )
    )

    server_config = (
        factory
        .build_server_config(
            profile,
            routes=[],
        )
    )

    daemon_config = (
        factory
        .build_daemon_config(
            profile
        )
    )

    eq(
        system_spec.worker_count,
        6,
        "profile factory maps worker count",
    )

    eq(
        system_spec.service_bindings[
            0
        ].instance_id,
        "svc-1",
        "profile factory preserves service bindings",
    )

    eq(
        system_spec.metadata[
            "runtime_profile"
        ],
        "production",
        "profile factory adds profile provenance",
    )

    eq(
        server_config.host,
        "0.0.0.0",
        "profile factory maps server host",
    )

    eq(
        server_config.recv_chunk_bytes,
        8192,
        "profile factory maps receive size",
    )

    eq(
        daemon_config.max_idle_timeouts,
        50,
        "profile factory maps daemon configuration",
    )


def test_defaults():
    codec = RuntimeProfileCodec()

    profile = codec.decode_text(
        '{"name":"minimal","storage_root":"data"}'
    )

    eq(
        profile.worker_count,
        4,
        "minimal profile default workers",
    )

    eq(
        profile.queue_capacity,
        128,
        "minimal profile default queue capacity",
    )

    eq(
        profile.host,
        "127.0.0.1",
        "minimal profile default host",
    )

    eq(
        profile.port,
        8080,
        "minimal profile default port",
    )


def test_validation():
    expect_error(
        ValueError,
        lambda: RuntimeProfile(
            "bad",
            "data",
            worker_count=0,
        ),
        "invalid worker count rejected",
    )

    expect_error(
        ValueError,
        lambda: RuntimeProfile(
            "bad",
            "data",
            port=70000,
        ),
        "invalid port rejected",
    )

    expect_error(
        ValueError,
        lambda: RuntimeProfile(
            "bad",
            "data",
            timeout_seconds=0,
        ),
        "invalid timeout rejected",
    )


def main():
    try:
        test_profile()
        test_codec_roundtrip()
        test_loader()
        test_filename_profile_match()
        test_factory_integration()
        test_defaults()
        test_validation()

    finally:
        cleanup()

    print(
        "RUNTIME CONFIG PROFILE TEST SUITE: PASS"
    )
    print(
        "Assertions passed:",
        ASSERTIONS,
    )
    print(
        "Files validated: 4/4"
    )
    print(
        "Typed deployment profile: VALIDATED"
    )
    print(
        "Handwritten JSON codec integration: VALIDATED"
    )
    print(
        "Traversal-safe profile loading: VALIDATED"
    )
    print(
        "RuntimeSystemSpec mapping: VALIDATED"
    )
    print(
        "RuntimeServerConfig mapping: VALIDATED"
    )
    print(
        "RuntimeDaemonConfig mapping: VALIDATED"
    )
    print(
        "Third-party dependencies: 0"
    )
    print(
        "Standard-library filesystem dependency: os"
    )


main()
