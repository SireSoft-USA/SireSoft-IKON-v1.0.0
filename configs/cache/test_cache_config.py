PARSERS_BASE = "libs/data/parsers/"
CACHE_BASE = "services/cache_service/"
CONFIG_BASE = "configs/cache/"

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
        CACHE_BASE,
        [
            "entry.py",
            "store.py",
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
    "cache.py",
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
            "cache config implementation contains forbidden import: "
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


def test_cache_config():
    cache = CacheConfig(
        "retrieval",
        max_entries=100,
        default_ttl_seconds=30,
        metadata={
            "purpose": "rag",
        },
    )

    eq(
        cache.cache_id,
        "retrieval",
        "cache config id",
    )

    eq(
        cache.to_dict()["metadata"]["purpose"],
        "rag",
        "cache metadata serialized",
    )


def test_codec():
    text = (
        '{"caches":['
        '{"cache_id":"retrieval","max_entries":10,'
        '"default_ttl_seconds":30},'
        '{"cache_id":"inference","max_entries":5,'
        '"enabled":false}'
        '],'
        '"persistence_path":"state/cache.bin"}'
    )

    config = CacheConfigCodec().decode_text(
        text
    )

    eq(
        len(config.caches),
        2,
        "codec cache count",
    )

    eq(
        len(config.enabled_caches()),
        1,
        "codec enabled cache count",
    )

    eq(
        config.persistence_path,
        "state/cache.bin",
        "codec persistence path",
    )


def test_duplicate_rejected():
    expect_error(
        ValueError,
        lambda: CacheServiceConfig(
            caches=[
                CacheConfig("same"),
                CacheConfig("same"),
            ],
        ),
        "duplicate cache id rejected",
    )


def test_validator():
    config = CacheServiceConfig(
        caches=[
            CacheConfig(
                "retrieval",
                max_entries=100,
                default_ttl_seconds=30,
            ),
            CacheConfig(
                "session",
                max_entries=50,
                default_ttl_seconds=None,
            ),
        ],
    )

    result = CacheConfigValidator().validate(
        config
    )

    eq(
        result["valid"],
        True,
        "cache config valid",
    )

    eq(
        result["total_capacity"],
        150,
        "validator totals cache capacity",
    )

    codes = [
        item["code"]
        for item in result["warnings"]
    ]

    check(
        "CACHE_WITHOUT_DEFAULT_TTL"
        in codes,
        "validator warns for no default TTL",
    )


def test_factory_manager():
    config = CacheServiceConfig(
        caches=[
            CacheConfig(
                "retrieval",
                max_entries=2,
                default_ttl_seconds=10,
            ),
            CacheConfig(
                "disabled",
                max_entries=2,
                enabled=False,
            ),
        ],
    )

    manager = CacheConfigFactory().build_manager(
        config
    )

    eq(
        manager.status(now=0)["cache_count"],
        1,
        "factory creates enabled cache only",
    )

    manager.set(
        "retrieval",
        "a",
        1,
        now=0,
    )

    manager.set(
        "retrieval",
        "b",
        2,
        now=0,
    )

    hit = manager.get(
        "retrieval",
        "a",
        now=1,
    )

    eq(
        hit["found"],
        True,
        "configured cache finds value",
    )

    eq(
        hit["value"],
        1,
        "configured cache returns stored value",
    )

    manager.set(
        "retrieval",
        "c",
        3,
        now=1,
    )

    miss = manager.get(
        "retrieval",
        "b",
        now=1,
        default="missing",
    )

    eq(
        miss["found"],
        False,
        "configured LRU evicts least-recently-used key",
    )

    eq(
        miss["value"],
        "missing",
        "configured LRU returns provided miss default",
    )

    expired = manager.get(
        "retrieval",
        "a",
        now=10,
        default="expired",
    )

    eq(
        expired["found"],
        False,
        "configured TTL expires at exact boundary",
    )

    eq(
        expired["value"],
        "expired",
        "expired lookup returns provided default",
    )


def test_initialize_without_persistence():
    config = CacheServiceConfig(
        caches=[
            CacheConfig(
                "one",
                3,
            ),
        ],
    )

    manager = CacheConfigFactory().initialize(
        config,
        load_persisted=False,
    )

    check(
        isinstance(
            manager,
            CacheManager,
        ),
        "initialize returns CacheManager",
    )

    eq(
        manager.status()["cache_count"],
        1,
        "initialize configures cache manager",
    )


def test_disabled_only_warning():
    config = CacheServiceConfig(
        caches=[
            CacheConfig(
                "off",
                enabled=False,
            ),
        ],
    )

    result = CacheConfigValidator().validate(
        config
    )

    codes = [
        item["code"]
        for item in result["warnings"]
    ]

    check(
        "NO_ENABLED_CACHES"
        in codes,
        "disabled-only config warned",
    )


def test_invalid_values():
    expect_error(
        ValueError,
        lambda: CacheConfig(
            "bad",
            max_entries=0,
        ),
        "zero cache capacity rejected",
    )

    expect_error(
        ValueError,
        lambda: CacheConfig(
            "bad",
            default_ttl_seconds=0,
        ),
        "zero default TTL rejected",
    )


def main():
    test_cache_config()
    test_codec()
    test_duplicate_rejected()
    test_validator()
    test_factory_manager()
    test_initialize_without_persistence()
    test_disabled_only_warning()
    test_invalid_values()

    print(
        "CACHE CONFIG TEST SUITE: PASS"
    )
    print(
        "Assertions passed:",
        ASSERTIONS,
    )
    print(
        "Files validated: 5/5"
    )
    print(
        "Typed named-cache configuration: VALIDATED"
    )
    print(
        "Handwritten JSON decoding: VALIDATED"
    )
    print(
        "Enabled-cache filtering: VALIDATED"
    )
    print(
        "CacheManager generation: VALIDATED"
    )
    print(
        "Configured LRU capacity: VALIDATED"
    )
    print(
        "Configured TTL semantics: VALIDATED"
    )
    print(
        "Persistence initialization boundary: VALIDATED"
    )
    print(
        "Third-party dependencies: 0"
    )


main()
