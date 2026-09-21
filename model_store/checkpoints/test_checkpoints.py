import os
import shutil

SERIAL_BASE = "libs/core/serialization/"
TRAINING_BASE = "libs/training/"
REGISTRY_BASE = "services/model_registry/"
STORE_BASE = "model_store/checkpoints/"

namespace = {
    "__builtins__": __builtins__,
}

for filename in [
    "binary_writer.py",
    "binary_reader.py",
    "checksum.py",
]:
    path = SERIAL_BASE + filename

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

path = TRAINING_BASE + "checkpoint.py"
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
    "model_version.py",
    "checkpoint_inspector.py",
    "registry.py",
]:
    path = REGISTRY_BASE + filename

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
    "artifact.py",
    "path_policy.py",
    "catalog.py",
    "store.py",
]:
    path = STORE_BASE + filename

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

TMP_ROOT = (
    "model_store/checkpoints/"
    "_test_store"
)

SOURCE_PATH = (
    "model_store/checkpoints/"
    "_test_source.sllmckpt"
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


def make_checkpoint(
    path,
):
    codec = CheckpointCodec()

    payload = {
        "format": "SireLLMCheckpoint",
        "version": 1,
        "model": {
            "token_embedding.weight": {
                "shape": [
                    2,
                    3,
                ],
                "data": [
                    0.1,
                    0.2,
                    0.3,
                    0.4,
                    0.5,
                    0.6,
                ],
            },
            "lm_head.weight": {
                "shape": [
                    3,
                    2,
                ],
                "data": [
                    1.0,
                    2.0,
                    3.0,
                    4.0,
                    5.0,
                    6.0,
                ],
            },
        },
        "optimizer": {
            "step": 10,
        },
        "scheduler": None,
        "trainer": {
            "epoch": 2,
        },
        "metadata": {
            "job_config": {
                "model": {
                    "vocab_size": 3,
                    "hidden_size": 2,
                    "num_layers": 1,
                },
            },
            "source": "unit-test",
        },
    }

    data = codec.encode(
        payload
    )

    handle = open(
        path,
        "wb",
    )

    try:
        handle.write(
            data
        )
    finally:
        handle.close()

    return payload


def build_store():
    return CheckpointStore(
        TMP_ROOT
    )


def test_path_policy():
    policy = CheckpointPathPolicy(
        "model_store_data"
    )

    eq(
        policy.artifact_path(
            "sirellm",
            "v1",
        ),
        (
            "model_store_data/"
            "sirellm/v1.sllmckpt"
        ),
        "deterministic artifact path",
    )

    expect_error(
        ValueError,
        lambda: policy.artifact_path(
            "../model",
            "v1",
        ),
        "model traversal rejected",
    )

    expect_error(
        ValueError,
        lambda: policy.artifact_path(
            "model",
            "v1/other",
        ),
        "version path separator rejected",
    )


def test_artifact():
    artifact = CheckpointArtifact(
        model_id="m",
        version="v1",
        path="/x",
        checksum="abc",
        byte_count=10,
        parameter_count=5,
        parameter_tensors=2,
        architecture={
            "hidden_size": 2,
        },
    )

    eq(
        artifact.key(),
        "m@v1",
        "artifact identity key",
    )

    eq(
        artifact.to_dict()[
            "parameter_count"
        ],
        5,
        "artifact parameter count",
    )


def test_put_and_inspect():
    store = build_store()

    artifact = store.put(
        model_id="sirellm",
        version="v1",
        source_path=(
            SOURCE_PATH
        ),
        metadata={
            "team": "core",
        },
    )

    check(
        os.path.exists(
            artifact.path
        ),
        "stored checkpoint file exists",
    )

    eq(
        artifact.parameter_count,
        12,
        "stored checkpoint parameter count inspected",
    )

    eq(
        artifact.parameter_tensors,
        2,
        "stored parameter tensor count inspected",
    )

    eq(
        artifact.architecture[
            "hidden_size"
        ],
        2,
        "architecture metadata extracted",
    )

    eq(
        artifact.metadata[
            "team"
        ],
        "core",
        "store metadata merged",
    )

    eq(
        store.status()[
            "artifact_count"
        ],
        1,
        "store artifact count",
    )


def test_source_destination_bytes_identical():
    store = build_store()

    artifact = store.put(
        "sirellm",
        "v1",
        SOURCE_PATH,
    )

    source = open(
        SOURCE_PATH,
        "rb",
    )

    stored = open(
        artifact.path,
        "rb",
    )

    try:
        eq(
            stored.read(),
            source.read(),
            "checkpoint copied byte-for-byte",
        )

    finally:
        source.close()
        stored.close()


def test_verify():
    store = build_store()

    store.put(
        "sirellm",
        "v1",
        SOURCE_PATH,
    )

    result = store.verify(
        "sirellm",
        "v1",
    )

    eq(
        result[
            "valid"
        ],
        True,
        "fresh stored checkpoint verifies",
    )

    eq(
        result[
            "checksum_match"
        ],
        True,
        "stored checkpoint checksum matches",
    )

    eq(
        result[
            "bytes_match"
        ],
        True,
        "stored checkpoint size matches",
    )


def test_tamper_detection():
    store = build_store()

    artifact = store.put(
        "sirellm",
        "v1",
        SOURCE_PATH,
    )

    handle = open(
        artifact.path,
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
        artifact.path,
        "wb",
    )

    try:
        handle.write(
            data
        )
    finally:
        handle.close()

    result = store.verify(
        "sirellm",
        "v1",
    )

    eq(
        result[
            "valid"
        ],
        False,
        "tampered stored checkpoint rejected",
    )

    eq(
        result[
            "checkpoint_valid"
        ],
        False,
        "checkpoint codec detects tampering",
    )


def test_immutability_duplicate():
    store = build_store()

    store.put(
        "sirellm",
        "v1",
        SOURCE_PATH,
    )

    expect_error(
        ValueError,
        lambda: store.put(
            "sirellm",
            "v1",
            SOURCE_PATH,
        ),
        "same model version cannot be overwritten",
    )


def test_existing_destination_rejected():
    store = build_store()

    destination = (
        store.path_policy
        .artifact_path(
            "sirellm",
            "v1",
        )
    )

    os.makedirs(
        os.path.dirname(
            destination
        ),
        exist_ok=True,
    )

    handle = open(
        destination,
        "wb",
    )

    try:
        handle.write(
            b"occupied"
        )
    finally:
        handle.close()

    expect_error(
        FileExistsError,
        lambda: store.put(
            "sirellm",
            "v1",
            SOURCE_PATH,
        ),
        "existing immutable destination is never overwritten",
    )

    eq(
        open(
            destination,
            "rb",
        ).read(),
        b"occupied",
        "existing file remains unchanged",
    )


def test_catalog_order():
    catalog = CheckpointCatalog()

    catalog.add(
        CheckpointArtifact(
            "model-a",
            "v1",
            "/a",
            "1",
            1,
            0,
            0,
        )
    )

    catalog.add(
        CheckpointArtifact(
            "model-a",
            "v2",
            "/b",
            "2",
            2,
            0,
            0,
        )
    )

    catalog.add(
        CheckpointArtifact(
            "model-b",
            "v1",
            "/c",
            "3",
            3,
            0,
            0,
        )
    )

    eq(
        catalog.models(),
        [
            {
                "model_id": "model-a",
                "versions": [
                    "v1",
                    "v2",
                ],
                "version_count": 2,
            },
            {
                "model_id": "model-b",
                "versions": [
                    "v1",
                ],
                "version_count": 1,
            },
        ],
        "catalog preserves model/version registration order",
    )


def test_catalog_state():
    catalog = CheckpointCatalog()

    catalog.add(
        CheckpointArtifact(
            "m",
            "v1",
            "/a",
            "abc",
            10,
            3,
            1,
            metadata={
                "x": 1,
            },
        )
    )

    state = catalog.export_state()

    restored = CheckpointCatalog()
    restored.load_state(
        state
    )

    eq(
        restored.export_state(),
        state,
        "catalog state exact round trip",
    )


def test_model_registry_integration():
    store = build_store()

    artifact = store.put(
        "sirellm",
        "v1",
        SOURCE_PATH,
    )

    registry = ModelRegistry()

    registered = (
        store
        .register_with_model_registry(
            registry,
            "sirellm",
            "v1",
            metadata={
                "storage": "model_store",
            },
            stage=True,
        )
    )

    eq(
        registered.checkpoint_path,
        artifact.path,
        "model registry points at immutable store artifact",
    )

    eq(
        registered.status,
        "staged",
        "store can register artifact as staged model",
    )

    eq(
        registered.checkpoint_checksum,
        artifact.checksum,
        "registry checksum matches store checksum",
    )

    eq(
        registry.verify(
            "sirellm",
            "v1",
        )[
            "valid"
        ],
        True,
        "model registry verifies stored artifact",
    )


def test_multiple_versions():
    store = build_store()

    store.put(
        "sirellm",
        "v1",
        SOURCE_PATH,
    )

    store.put(
        "sirellm",
        "v2",
        SOURCE_PATH,
        metadata={
            "note": "second",
        },
    )

    versions = store.list_versions(
        "sirellm"
    )

    eq(
        [
            row[
                "version"
            ]
            for row in versions
        ],
        [
            "v1",
            "v2",
        ],
        "store preserves version order",
    )

    eq(
        store.status()[
            "model_count"
        ],
        1,
        "multiple versions still one model",
    )

    eq(
        store.status()[
            "artifact_count"
        ],
        2,
        "multiple versions counted as artifacts",
    )


def test_invalid_checkpoint_cleanup():
    invalid_path = (
        "model_store/checkpoints/"
        "_invalid.sllmckpt"
    )

    handle = open(
        invalid_path,
        "wb",
    )

    try:
        handle.write(
            b"not-a-checkpoint"
        )
    finally:
        handle.close()

    try:
        store = build_store()

        expect_error(
            ValueError,
            lambda: store.put(
                "bad",
                "v1",
                invalid_path,
            ),
            "invalid source checkpoint rejected",
        )

        destination = (
            store.path_policy
            .artifact_path(
                "bad",
                "v1",
            )
        )

        eq(
            os.path.exists(
                destination
            ),
            False,
            "invalid source creates no stored artifact",
        )

    finally:
        if os.path.exists(
            invalid_path
        ):
            os.remove(
                invalid_path
            )


def test_metadata_copy_isolation():
    store = build_store()

    metadata = {
        "tags": [
            "a",
        ],
    }

    artifact = store.put(
        "sirellm",
        "v1",
        SOURCE_PATH,
        metadata=metadata,
    )

    metadata[
        "tags"
    ].append(
        "mutated"
    )

    eq(
        artifact.metadata[
            "tags"
        ],
        [
            "a",
        ],
        "artifact metadata isolated from caller mutation",
    )


def main():
    if os.path.exists(
        TMP_ROOT
    ):
        shutil.rmtree(
            TMP_ROOT
        )

    if os.path.exists(
        SOURCE_PATH
    ):
        os.remove(
            SOURCE_PATH
        )

    make_checkpoint(
        SOURCE_PATH
    )

    try:
        tests = [
            test_path_policy,
            test_artifact,
            test_put_and_inspect,
            test_source_destination_bytes_identical,
            test_verify,
            test_tamper_detection,
            test_immutability_duplicate,
            test_existing_destination_rejected,
            test_catalog_order,
            test_catalog_state,
            test_model_registry_integration,
            test_multiple_versions,
            test_invalid_checkpoint_cleanup,
            test_metadata_copy_isolation,
        ]

        for test in tests:
            if os.path.exists(
                TMP_ROOT
            ):
                shutil.rmtree(
                    TMP_ROOT
                )

            test()

    finally:
        if os.path.exists(
            TMP_ROOT
        ):
            shutil.rmtree(
                TMP_ROOT
            )

        if os.path.exists(
            SOURCE_PATH
        ):
            os.remove(
                SOURCE_PATH
            )

    print(
        "MODEL STORE CHECKPOINTS TEST SUITE: PASS"
    )
    print(
        "Assertions passed:",
        ASSERTIONS,
    )
    print(
        "Files validated: 4/4"
    )
    print(
        "Safe deterministic artifact paths: VALIDATED"
    )
    print(
        "Checkpoint validation before storage: VALIDATED"
    )
    print(
        "Immutable byte-for-byte checkpoint copies: VALIDATED"
    )
    print(
        "Checksum/tamper verification: VALIDATED"
    )
    print(
        "Deterministic model/version catalog: VALIDATED"
    )
    print(
        "Model Registry integration: VALIDATED"
    )
    print(
        "Third-party dependencies: 0"
    )
    print(
        "Standard-library filesystem dependency: os"
    )


main()
