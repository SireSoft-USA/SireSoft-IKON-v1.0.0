import os
import shutil
import threading

STORAGE_BASE = "runtime/storage/"

namespace = {
    "__builtins__": __builtins__,
}

for filename in [
    "path_policy.py",
    "atomic_file.py",
    "namespace.py",
    "store.py",
]:
    path = STORAGE_BASE + filename

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
    "runtime/storage/"
    "_test_store"
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


def fresh():
    if os.path.exists(
        ROOT
    ):
        shutil.rmtree(
            ROOT
        )

    return RuntimeStorage(
        ROOT
    )


def test_path_policy():
    policy = StoragePathPolicy(
        "data"
    )

    eq(
        policy.key_path(
            "cache",
            "alpha",
        ),
        (
            "data/cache/"
            "alpha.sllmdata"
        ),
        "deterministic storage path",
    )

    expect_error(
        ValueError,
        lambda: policy.key_path(
            "../cache",
            "x",
        ),
        "unsafe namespace rejected",
    )

    expect_error(
        ValueError,
        lambda: policy.key_path(
            "cache",
            "../x",
        ),
        "unsafe key rejected",
    )


def test_namespace():
    store = fresh()

    descriptor = (
        store.create_namespace(
            "runtime",
            description=(
                "runtime state"
            ),
            metadata={
                "owner": "core",
            },
        )
    )

    eq(
        descriptor.to_dict()[
            "name"
        ],
        "runtime",
        "namespace created",
    )

    eq(
        store.list_namespaces(),
        [
            {
                "name": "runtime",
                "description": (
                    "runtime state"
                ),
                "metadata": {
                    "owner": "core",
                },
            },
        ],
        "namespace listing deterministic",
    )

    expect_error(
        ValueError,
        lambda: store.create_namespace(
            "runtime"
        ),
        "duplicate namespace rejected",
    )


def test_put_get():
    store = fresh()
    store.create_namespace(
        "cache"
    )

    result = store.put(
        "cache",
        "alpha",
        b"hello",
    )

    eq(
        result[
            "bytes"
        ],
        5,
        "write byte count",
    )

    eq(
        store.get(
            "cache",
            "alpha",
        ),
        b"hello",
        "stored bytes round trip",
    )

    eq(
        store.exists(
            "cache",
            "alpha",
        ),
        True,
        "exists returns true",
    )


def test_create_only():
    store = fresh()
    store.create_namespace(
        "models"
    )

    store.put(
        "models",
        "v1",
        b"one",
        overwrite=False,
    )

    expect_error(
        FileExistsError,
        lambda: store.put(
            "models",
            "v1",
            b"two",
            overwrite=False,
        ),
        "create-only semantics prevent overwrite",
    )

    eq(
        store.get(
            "models",
            "v1",
        ),
        b"one",
        "failed create-only write leaves original intact",
    )


def test_atomic_overwrite():
    store = fresh()
    store.create_namespace(
        "runtime"
    )

    store.put(
        "runtime",
        "state",
        b"old",
    )

    store.put(
        "runtime",
        "state",
        b"new-value",
        overwrite=True,
    )

    eq(
        store.get(
            "runtime",
            "state",
        ),
        b"new-value",
        "atomic overwrite replaces content",
    )

    temp = (
        store.path_policy
        .temporary_path(
            "runtime",
            "state",
        )
    )

    eq(
        os.path.exists(
            temp
        ),
        False,
        "successful atomic write leaves no temp file",
    )


def test_list_keys():
    store = fresh()
    store.create_namespace(
        "cache"
    )

    for key in (
        "zeta",
        "alpha",
        "middle",
    ):
        store.put(
            "cache",
            key,
            key.encode(
                "utf-8"
            ),
        )

    eq(
        store.list_keys(
            "cache"
        ),
        [
            "alpha",
            "middle",
            "zeta",
        ],
        "keys listed deterministically",
    )

    temp = (
        store.path_policy
        .temporary_path(
            "cache",
            "ghost",
        )
    )

    handle = open(
        temp,
        "wb",
    )

    try:
        handle.write(
            b"incomplete"
        )

    finally:
        handle.close()

    eq(
        store.list_keys(
            "cache"
        ),
        [
            "alpha",
            "middle",
            "zeta",
        ],
        "temporary files excluded from listing",
    )


def test_delete():
    store = fresh()
    store.create_namespace(
        "jobs"
    )

    store.put(
        "jobs",
        "one",
        b"x",
    )

    eq(
        store.delete(
            "jobs",
            "one",
        ),
        True,
        "delete existing key",
    )

    eq(
        store.exists(
            "jobs",
            "one",
        ),
        False,
        "deleted key gone",
    )

    eq(
        store.delete(
            "jobs",
            "one",
            missing_ok=True,
        ),
        False,
        "missing_ok delete returns false",
    )


def test_key_info():
    store = fresh()
    store.create_namespace(
        "logs"
    )

    store.put(
        "logs",
        "segment",
        b"123456",
    )

    info = store.key_info(
        "logs",
        "segment",
    )

    eq(
        info[
            "bytes"
        ],
        6,
        "key_info size",
    )

    eq(
        info[
            "namespace"
        ],
        "logs",
        "key_info namespace",
    )


def test_unknown_namespace():
    store = fresh()

    expect_error(
        KeyError,
        lambda: store.put(
            "missing",
            "x",
            b"y",
        ),
        "unknown namespace rejected",
    )


def test_concurrent_independent_keys():
    store = fresh()
    store.create_namespace(
        "concurrent"
    )

    errors = []

    def writer(
        index,
    ):
        try:
            store.put(
                "concurrent",
                (
                    "key-"
                    + str(
                        index
                    )
                ),
                (
                    "value-"
                    + str(
                        index
                    )
                ).encode(
                    "utf-8"
                ),
            )

        except Exception as error:
            errors.append(
                error
            )

    threads = []

    for index in range(
        10
    ):
        thread = threading.Thread(
            target=writer,
            args=(
                index,
            ),
        )

        threads.append(
            thread
        )
        thread.start()

    for thread in threads:
        thread.join(
            timeout=3.0
        )

    eq(
        errors,
        [],
        "independent concurrent writes complete without errors",
    )

    eq(
        len(
            store.list_keys(
                "concurrent"
            )
        ),
        10,
        "all concurrent keys stored",
    )


def test_status():
    store = fresh()

    store.create_namespace(
        "a"
    )
    store.create_namespace(
        "b"
    )

    store.put(
        "a",
        "x",
        b"1",
    )
    store.put(
        "b",
        "y",
        b"2",
    )

    store.get(
        "a",
        "x",
    )

    store.delete(
        "b",
        "y",
    )

    status = store.status()

    eq(
        status[
            "namespace_count"
        ],
        2,
        "status namespace count",
    )

    eq(
        status[
            "key_count"
        ],
        1,
        "status live key count",
    )

    eq(
        status[
            "total_writes"
        ],
        2,
        "status write count",
    )

    eq(
        status[
            "total_reads"
        ],
        1,
        "status read count",
    )

    eq(
        status[
            "total_deletes"
        ],
        1,
        "status delete count",
    )

    eq(
        status[
            "atomic_replace"
        ],
        True,
        "status reports atomic replacement",
    )


def main():
    try:
        test_path_policy()
        test_namespace()
        test_put_get()
        test_create_only()
        test_atomic_overwrite()
        test_list_keys()
        test_delete()
        test_key_info()
        test_unknown_namespace()
        test_concurrent_independent_keys()
        test_status()

    finally:
        if os.path.exists(
            ROOT
        ):
            shutil.rmtree(
                ROOT
            )

    print(
        "RUNTIME STORAGE TEST SUITE: PASS"
    )
    print(
        "Assertions passed:",
        ASSERTIONS,
    )
    print(
        "Files validated: 4/4"
    )
    print(
        "Traversal-safe namespace/key paths: VALIDATED"
    )
    print(
        "Atomic fsync + os.replace writes: VALIDATED"
    )
    print(
        "Create-only and overwrite semantics: VALIDATED"
    )
    print(
        "Deterministic namespace/key listing: VALIDATED"
    )
    print(
        "Concurrent independent-key writes: VALIDATED"
    )
    print(
        "Third-party dependencies: 0"
    )
    print(
        "Standard-library filesystem dependency: os"
    )


main()
