import os

SERIAL_BASE = "libs/core/serialization/"
PROTOCOL_BASE = "libs/protocol/"
SERVICE_BASE = "services/cache_service/"

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
        PROTOCOL_BASE,
        [
            "error.py",
            "message.py",
            "request.py",
            "response.py",
            "validator.py",
            "codec.py",
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
    "entry.py",
    "store.py",
    "persistence.py",
    "manager.py",
    "service.py",
]:
    path = SERVICE_BASE + filename

    source = open(
        path,
        "r",
        encoding="utf-8",
    ).read()

    if "import " in source:
        raise AssertionError(
            "cache_service implementation contains forbidden import: "
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
    "services/cache_service/"
    "_test_cache_state.slcache"
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
        + repr(
            actual
        )
        + " expected="
        + repr(
            expected
        )
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


def manager():
    worker = CacheManager()

    worker.create_cache(
        "responses",
        max_entries=3,
        default_ttl_seconds=30,
    )

    worker.create_cache(
        "embeddings",
        max_entries=2,
        default_ttl_seconds=None,
    )

    return worker


def test_basic_set_get():
    worker = manager()

    result = worker.set(
        "responses",
        "q1",
        {
            "answer": "hello",
        },
        now=100,
        metadata={
            "source": "rag",
        },
    )

    eq(
        result[
            "replaced"
        ],
        False,
        "first set is not replacement",
    )

    fetched = worker.get(
        "responses",
        "q1",
        now=101,
    )

    eq(
        fetched[
            "found"
        ],
        True,
        "cache hit found",
    )

    eq(
        fetched[
            "value"
        ][
            "answer"
        ],
        "hello",
        "cached value preserved",
    )

    eq(
        fetched[
            "entry"
        ][
            "metadata"
        ][
            "source"
        ],
        "rag",
        "cache metadata preserved",
    )


def test_copy_isolation():
    worker = manager()

    original = {
        "nested": [
            1,
            2,
        ],
    }

    worker.set(
        "responses",
        "copy",
        original,
        now=1,
    )

    original[
        "nested"
    ].append(
        3
    )

    fetched = worker.get(
        "responses",
        "copy",
        now=2,
    )

    eq(
        fetched[
            "value"
        ],
        {
            "nested": [
                1,
                2,
            ],
        },
        "set copies caller value",
    )

    fetched[
        "value"
    ][
        "nested"
    ].append(
        99
    )

    again = worker.get(
        "responses",
        "copy",
        now=3,
    )

    eq(
        again[
            "value"
        ],
        {
            "nested": [
                1,
                2,
            ],
        },
        "get returns isolated copy",
    )


def test_ttl_boundary():
    worker = manager()

    worker.set(
        "responses",
        "ttl",
        "value",
        now=100,
        ttl_seconds=10,
    )

    before = worker.get(
        "responses",
        "ttl",
        now=109,
    )

    eq(
        before[
            "found"
        ],
        True,
        "entry available before TTL boundary",
    )

    at_boundary = worker.get(
        "responses",
        "ttl",
        now=110,
    )

    eq(
        at_boundary[
            "found"
        ],
        False,
        "entry expired exactly at expires_at",
    )

    stats = worker.get_cache(
        "responses"
    ).stats()

    eq(
        stats[
            "expirations"
        ],
        1,
        "expiration counted",
    )


def test_default_ttl():
    worker = manager()

    worker.set(
        "responses",
        "default-ttl",
        "value",
        now=1,
    )

    peek = worker.peek(
        "responses",
        "default-ttl",
        now=30,
    )

    eq(
        peek[
            "found"
        ],
        True,
        "default TTL active before boundary",
    )

    expired = worker.peek(
        "responses",
        "default-ttl",
        now=31,
    )

    eq(
        expired[
            "found"
        ],
        False,
        "default TTL expires at boundary",
    )


def test_lru_eviction():
    worker = manager()

    worker.set(
        "responses",
        "a",
        "A",
        now=1,
    )

    worker.set(
        "responses",
        "b",
        "B",
        now=1,
    )

    worker.set(
        "responses",
        "c",
        "C",
        now=1,
    )

    worker.get(
        "responses",
        "a",
        now=2,
    )

    worker.get(
        "responses",
        "c",
        now=2,
    )

    inserted = worker.set(
        "responses",
        "d",
        "D",
        now=3,
    )

    eq(
        inserted[
            "evicted_keys"
        ],
        [
            "b",
        ],
        "least recently accessed entry evicted",
    )

    eq(
        worker.peek(
            "responses",
            "b",
            now=3,
        )[
            "found"
        ],
        False,
        "evicted key unavailable",
    )

    eq(
        worker.get_cache(
            "responses"
        ).stats()[
            "evictions"
        ],
        1,
        "eviction count",
    )


def test_replacement_does_not_grow():
    worker = manager()

    worker.set(
        "responses",
        "same",
        1,
        now=1,
    )

    replacement = worker.set(
        "responses",
        "same",
        2,
        now=2,
    )

    eq(
        replacement[
            "replaced"
        ],
        True,
        "replacement reported",
    )

    eq(
        worker.get_cache(
            "responses"
        ).count(),
        1,
        "replacement does not grow cache",
    )

    eq(
        worker.get(
            "responses",
            "same",
            now=3,
        )[
            "value"
        ],
        2,
        "replacement value stored",
    )


def test_peek_does_not_change_hit_stats():
    worker = manager()

    worker.set(
        "responses",
        "x",
        1,
        now=1,
    )

    worker.peek(
        "responses",
        "x",
        now=2,
    )

    stats = worker.get_cache(
        "responses"
    ).stats()

    eq(
        stats[
            "hits"
        ],
        0,
        "peek does not count cache hit",
    )

    worker.get(
        "responses",
        "x",
        now=2,
    )

    eq(
        worker.get_cache(
            "responses"
        ).stats()[
            "hits"
        ],
        1,
        "get counts hit",
    )


def test_miss_stats():
    worker = manager()

    missing = worker.get(
        "responses",
        "missing",
        now=1,
        default={
            "fallback": True,
        },
    )

    eq(
        missing[
            "found"
        ],
        False,
        "missing key returns found false",
    )

    eq(
        missing[
            "value"
        ],
        {
            "fallback": True,
        },
        "missing key returns default copy",
    )

    eq(
        worker.get_cache(
            "responses"
        ).stats()[
            "misses"
        ],
        1,
        "miss counted",
    )


def test_named_cache_isolation():
    worker = manager()

    worker.set(
        "responses",
        "same",
        "response",
        now=1,
    )

    worker.set(
        "embeddings",
        "same",
        [
            0.1,
            0.2,
        ],
        now=1,
    )

    eq(
        worker.get(
            "responses",
            "same",
            now=2,
        )[
            "value"
        ],
        "response",
        "response cache isolated",
    )

    eq(
        worker.get(
            "embeddings",
            "same",
            now=2,
        )[
            "value"
        ],
        [
            0.1,
            0.2,
        ],
        "embedding cache isolated",
    )


def test_delete_clear_purge():
    worker = manager()

    worker.set(
        "responses",
        "a",
        1,
        now=1,
        ttl_seconds=1,
    )

    worker.set(
        "responses",
        "b",
        2,
        now=1,
        ttl_seconds=10,
    )

    purged = worker.purge_expired(
        "responses",
        now=2,
    )

    eq(
        purged[
            "expired_keys"
        ],
        [
            "a",
        ],
        "purge removes expired key",
    )

    deleted = worker.delete(
        "responses",
        "b",
    )

    eq(
        deleted[
            "deleted"
        ],
        True,
        "delete existing key",
    )

    worker.set(
        "responses",
        "c",
        3,
        now=3,
    )

    worker.set(
        "responses",
        "d",
        4,
        now=3,
    )

    cleared = worker.clear(
        "responses"
    )

    eq(
        cleared[
            "cleared_entries"
        ],
        2,
        "clear reports entry count",
    )

    eq(
        worker.get_cache(
            "responses"
        ).count(),
        0,
        "cache empty after clear",
    )


def test_manager_status():
    worker = manager()

    worker.set(
        "responses",
        "a",
        1,
        now=1,
    )

    worker.get(
        "responses",
        "a",
        now=2,
    )

    worker.get(
        "responses",
        "missing",
        now=2,
    )

    status = worker.status(
        now=2
    )

    eq(
        status[
            "cache_count"
        ],
        2,
        "manager cache count",
    )

    eq(
        status[
            "total_entries"
        ],
        1,
        "manager entry count",
    )

    eq(
        status[
            "total_hits"
        ],
        1,
        "manager hit total",
    )

    eq(
        status[
            "total_misses"
        ],
        1,
        "manager miss total",
    )

    eq(
        status[
            "eviction_policy"
        ],
        "lru",
        "manager reports LRU",
    )


def test_state_round_trip():
    if os.path.exists(
        STATE_PATH
    ):
        os.remove(
            STATE_PATH
        )

    source = manager()

    source.set(
        "responses",
        "rag:query",
        {
            "answer": "cached",
            "citations": [
                "S1",
            ],
        },
        now=100,
        ttl_seconds=60,
    )

    source.get(
        "responses",
        "rag:query",
        now=101,
    )

    source.set(
        "embeddings",
        "text:x",
        [
            0.1,
            0.2,
            0.3,
        ],
        now=100,
    )

    before = source.export_state()

    saved = source.save_state(
        STATE_PATH
    )

    check(
        saved[
            "bytes"
        ] > 0,
        "cache state written",
    )

    restored = CacheManager()

    restored.load_state_file(
        STATE_PATH
    )

    eq(
        restored.export_state(),
        before,
        "cache manager state exact round trip",
    )

    eq(
        restored.get(
            "responses",
            "rag:query",
            now=102,
        )[
            "value"
        ][
            "answer"
        ],
        "cached",
        "restored cache value accessible",
    )


def test_state_corruption_detection():
    worker = manager()

    worker.set(
        "responses",
        "x",
        "value",
        now=1,
    )

    worker.save_state(
        STATE_PATH
    )

    handle = open(
        STATE_PATH,
        "rb",
    )

    try:
        data = bytearray(
            handle.read()
        )
    finally:
        handle.close()

    data[
        -1
    ] ^= 0x01

    handle = open(
        STATE_PATH,
        "wb",
    )

    try:
        handle.write(
            data
        )
    finally:
        handle.close()

    expect_error(
        ValueError,
        lambda: CacheManager().load_state_file(
            STATE_PATH
        ),
        "cache state checksum detects corruption",
    )


def test_service_flow():
    service = CacheService()

    created = service.handle(
        ServiceRequest(
            "s1",
            "cache_service",
            "create_cache",
            payload={
                "cache_id": "rag",
                "max_entries": 2,
                "default_ttl_seconds": 60,
            },
        )
    )

    eq(
        created.success,
        True,
        "service creates cache",
    )

    set_response = service.handle(
        ServiceRequest(
            "s2",
            "cache_service",
            "set",
            payload={
                "cache_id": "rag",
                "key": "q1",
                "value": {
                    "answer": "hello",
                },
                "now": 100,
            },
        )
    )

    eq(
        set_response.success,
        True,
        "service set succeeds",
    )

    fetched = service.handle(
        ServiceRequest(
            "s3",
            "cache_service",
            "get",
            payload={
                "cache_id": "rag",
                "key": "q1",
                "now": 101,
            },
        )
    )

    eq(
        fetched.data[
            "result"
        ][
            "value"
        ][
            "answer"
        ],
        "hello",
        "service get returns cached value",
    )

    status = service.handle(
        ServiceRequest(
            "s4",
            "cache_service",
            "status",
            payload={
                "now": 101,
            },
        )
    )

    eq(
        status.data[
            "status"
        ][
            "cache_count"
        ],
        1,
        "service status cache count",
    )


def test_protocol_round_trip():
    worker = CacheManager()

    worker.create_cache(
        "rag",
        max_entries=2,
    )

    service = CacheService(
        worker
    )

    codec = ProtocolCodec()

    request = ServiceRequest(
        "protocol-cache",
        "cache_service",
        "set",
        payload={
            "cache_id": "rag",
            "key": "answer",
            "value": {
                "text": "cached",
                "citations": [
                    "S1",
                ],
            },
            "now": 1,
        },
        trace_id="trace-cache",
    )

    request = (
        codec.decode_request(
            codec.encode_request(
                request
            )
        )
    )

    response = service.handle(
        request
    )

    response = (
        codec.decode_response(
            codec.encode_response(
                response
            )
        )
    )

    eq(
        response.success,
        True,
        "cache set survives protocol codec",
    )

    eq(
        response.trace_id,
        "trace-cache",
        "cache trace preserved",
    )

    get_request = ServiceRequest(
        "protocol-cache-get",
        "cache_service",
        "get",
        payload={
            "cache_id": "rag",
            "key": "answer",
            "now": 2,
        },
    )

    get_request = (
        codec.decode_request(
            codec.encode_request(
                get_request
            )
        )
    )

    get_response = service.handle(
        get_request
    )

    get_response = (
        codec.decode_response(
            codec.encode_response(
                get_response
            )
        )
    )

    eq(
        get_response.data[
            "result"
        ][
            "value"
        ][
            "citations"
        ],
        [
            "S1",
        ],
        "cached structured value survives protocol",
    )


def test_errors():
    service = CacheService()

    missing_cache = service.handle(
        ServiceRequest(
            "e1",
            "cache_service",
            "get",
            payload={
                "cache_id": "missing",
                "key": "x",
                "now": 1,
            },
        )
    )

    eq(
        missing_cache.error.code,
        "NOT_FOUND",
        "missing cache maps to NOT_FOUND",
    )

    invalid = service.handle(
        ServiceRequest(
            "e2",
            "cache_service",
            "create_cache",
            payload={
                "cache_id": "bad",
                "max_entries": 0,
            },
        )
    )

    eq(
        invalid.error.code,
        "INVALID_REQUEST",
        "invalid cache configuration rejected",
    )

    wrong = service.handle(
        ServiceRequest(
            "e3",
            "rag_service",
            "status",
        )
    )

    eq(
        wrong.error.code,
        "INVALID_REQUEST",
        "wrong target service rejected",
    )

    expect_error(
        TypeError,
        lambda: service.handle(
            {}
        ),
        "non-ServiceRequest rejected",
    )


def test_validation():
    expect_error(
        ValueError,
        lambda: InMemoryCache(
            "",
        ),
        "empty cache ID rejected",
    )

    expect_error(
        ValueError,
        lambda: CacheEntry(
            key="x",
            value=1,
            created_at=10,
            expires_at=10,
        ),
        "non-future expiry rejected",
    )

    worker = manager()

    expect_error(
        ValueError,
        lambda: worker.set(
            "responses",
            "x",
            1,
            now=1,
            ttl_seconds=0,
        ),
        "zero TTL rejected",
    )


def main():
    try:
        test_basic_set_get()
        test_copy_isolation()
        test_ttl_boundary()
        test_default_ttl()
        test_lru_eviction()
        test_replacement_does_not_grow()
        test_peek_does_not_change_hit_stats()
        test_miss_stats()
        test_named_cache_isolation()
        test_delete_clear_purge()
        test_manager_status()
        test_state_round_trip()
        test_state_corruption_detection()
        test_service_flow()
        test_protocol_round_trip()
        test_errors()
        test_validation()

    finally:
        if os.path.exists(
            STATE_PATH
        ):
            os.remove(
                STATE_PATH
            )

    print(
        "CACHE SERVICE TEST SUITE: PASS"
    )
    print(
        "Assertions passed:",
        ASSERTIONS,
    )
    print(
        "Files validated: 5/5"
    )
    print(
        "Named cache isolation: VALIDATED"
    )
    print(
        "TTL expiry/boundary semantics: VALIDATED"
    )
    print(
        "Deterministic LRU eviction: VALIDATED"
    )
    print(
        "Hit/miss/eviction accounting: VALIDATED"
    )
    print(
        "Deep-copy value isolation: VALIDATED"
    )
    print(
        "Binary state persistence/checksum: VALIDATED"
    )
    print(
        "Structured RAG-style cache values: VALIDATED"
    )
    print(
        "Protocol service operations: VALIDATED"
    )
    print(
        "Third-party dependencies: 0"
    )


main()
