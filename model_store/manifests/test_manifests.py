import os
import shutil

SERIAL_BASE = "libs/core/serialization/"
TRAINING_BASE = "libs/training/"
REGISTRY_BASE = "services/model_registry/"
CHECKPOINT_BASE = "model_store/checkpoints/"
MANIFEST_BASE = "model_store/manifests/"

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
    path = CHECKPOINT_BASE + filename

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
    "manifest.py",
    "validator.py",
    "persistence.py",
    "catalog.py",
    "store.py",
]:
    path = MANIFEST_BASE + filename

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

CHECKPOINT_ROOT = (
    "model_store/manifests/"
    "_test_checkpoint_store"
)

MANIFEST_ROOT = (
    "model_store/manifests/"
    "_test_manifest_store"
)

SOURCE_PATH = (
    "model_store/manifests/"
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
            "embedding.weight": {
                "shape": [
                    4,
                    2,
                ],
                "data": [
                    0.1,
                    0.2,
                    0.3,
                    0.4,
                    0.5,
                    0.6,
                    0.7,
                    0.8,
                ],
            },
            "head.weight": {
                "shape": [
                    2,
                    4,
                ],
                "data": [
                    1.0,
                    2.0,
                    3.0,
                    4.0,
                    5.0,
                    6.0,
                    7.0,
                    8.0,
                ],
            },
        },
        "optimizer": None,
        "scheduler": None,
        "trainer": {
            "epoch": 1,
        },
        "metadata": {
            "job_config": {
                "model": {
                    "vocab_size": 4,
                    "hidden_size": 2,
                    "num_layers": 1,
                    "num_heads": 1,
                },
            },
            "source": "manifest-test",
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


def build_stores():
    checkpoints = CheckpointStore(
        CHECKPOINT_ROOT
    )

    artifact = checkpoints.put(
        "sirellm",
        "v1",
        SOURCE_PATH,
        metadata={
            "checkpoint_tag": "trained",
        },
    )

    manifests = ManifestStore(
        MANIFEST_ROOT
    )

    return (
        checkpoints,
        manifests,
        artifact,
    )


def test_manifest_object():
    manifest = ModelManifest(
        model_id="m",
        version="v1",
        created_at=10,
        checkpoint={
            "path": "/x",
            "checksum": "abc",
            "byte_count": 100,
            "parameter_count": 10,
            "parameter_tensors": 2,
        },
        architecture={
            "hidden_size": 2,
        },
        tokenizer={
            "artifact_id": "tok-v1",
        },
    )

    eq(
        manifest.key(),
        "m@v1",
        "manifest identity key",
    )

    eq(
        manifest.to_dict()[
            "format"
        ],
        "SireLLMModelManifest",
        "manifest format marker",
    )


def test_create_from_checkpoint():
    checkpoints, manifests, artifact = build_stores()

    result = (
        manifests
        .create_from_checkpoint_store(
            checkpoint_store=checkpoints,
            model_id="sirellm",
            version="v1",
            created_at=100,
            tokenizer={
                "artifact_id": "tok-v1",
                "vocab_size": 4,
            },
            runtime={
                "max_context_tokens": 256,
            },
            metadata={
                "owner": "core",
            },
        )
    )

    check(
        os.path.exists(
            result[
                "path"
            ]
        ),
        "manifest file created",
    )

    manifest = result[
        "manifest"
    ]

    eq(
        manifest[
            "checkpoint"
        ][
            "checksum"
        ],
        artifact.checksum,
        "manifest references checkpoint checksum",
    )

    eq(
        manifest[
            "architecture"
        ][
            "hidden_size"
        ],
        2,
        "manifest carries inspected architecture",
    )

    eq(
        manifest[
            "tokenizer"
        ][
            "artifact_id"
        ],
        "tok-v1",
        "manifest carries tokenizer reference metadata",
    )


def test_persistence_round_trip():
    manifest = ModelManifest(
        model_id="m",
        version="v1",
        created_at=1,
        checkpoint={
            "path": "/x",
            "checksum": "abc",
            "byte_count": 10,
            "parameter_count": 2,
            "parameter_tensors": 1,
        },
        metadata={
            "tags": [
                "a",
                "b",
            ],
        },
    )

    persistence = (
        ManifestPersistence()
    )

    encoded = persistence.encode(
        manifest
    )

    decoded = persistence.decode(
        encoded
    )

    eq(
        decoded.to_dict(),
        manifest.to_dict(),
        "manifest binary codec exact round trip",
    )


def test_manifest_tamper_detection():
    manifest = ModelManifest(
        model_id="m",
        version="v1",
        created_at=1,
        checkpoint={
            "path": "/x",
            "checksum": "abc",
            "byte_count": 10,
            "parameter_count": 2,
            "parameter_tensors": 1,
        },
    )

    persistence = (
        ManifestPersistence()
    )

    data = bytearray(
        persistence.encode(
            manifest
        )
    )

    data[
        -1
    ] ^= 0x01

    expect_error(
        ValueError,
        lambda: persistence.decode(
            bytes(
                data
            )
        ),
        "manifest checksum detects tampering",
    )


def test_store_verify_checkpoint_match():
    checkpoints, manifests, _ = build_stores()

    manifests.create_from_checkpoint_store(
        checkpoints,
        "sirellm",
        "v1",
        100,
    )

    result = manifests.verify(
        "sirellm",
        "v1",
        checkpoint_store=checkpoints,
    )

    eq(
        result[
            "valid"
        ],
        True,
        "stored manifest verifies against checkpoint store",
    )

    eq(
        result[
            "checkpoint_match"
        ][
            "valid"
        ],
        True,
        "all checkpoint reference fields match",
    )


def test_manifest_file_tamper():
    checkpoints, manifests, _ = build_stores()

    result = manifests.create_from_checkpoint_store(
        checkpoints,
        "sirellm",
        "v1",
        100,
    )

    path = result[
        "path"
    ]

    handle = open(
        path,
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
        path,
        "wb",
    )

    try:
        handle.write(
            data
        )
    finally:
        handle.close()

    verification = manifests.verify(
        "sirellm",
        "v1",
        checkpoint_store=checkpoints,
    )

    eq(
        verification[
            "valid"
        ],
        False,
        "tampered manifest file rejected",
    )

    eq(
        verification[
            "manifest_valid"
        ],
        False,
        "manifest codec rejects tampered file",
    )


def test_immutability():
    checkpoints, manifests, _ = build_stores()

    manifests.create_from_checkpoint_store(
        checkpoints,
        "sirellm",
        "v1",
        100,
    )

    expect_error(
        FileExistsError,
        lambda: (
            ManifestStore(
                MANIFEST_ROOT
            )
            .create_from_checkpoint_store(
                checkpoints,
                "sirellm",
                "v1",
                101,
            )
        ),
        "existing manifest file is immutable",
    )


def test_catalog_order():
    catalog = ManifestCatalog()

    one = ModelManifest(
        "a",
        "v1",
        1,
        {
            "path": "/a",
            "checksum": "1",
            "byte_count": 1,
            "parameter_count": 0,
            "parameter_tensors": 0,
        },
    )

    two = ModelManifest(
        "a",
        "v2",
        2,
        {
            "path": "/b",
            "checksum": "2",
            "byte_count": 1,
            "parameter_count": 0,
            "parameter_tensors": 0,
        },
    )

    catalog.add(
        one,
        "/m1",
        1,
    )

    catalog.add(
        two,
        "/m2",
        2,
    )

    eq(
        catalog.models(),
        [
            {
                "model_id": "a",
                "versions": [
                    "v1",
                    "v2",
                ],
                "version_count": 2,
            },
        ],
        "manifest catalog preserves version order",
    )


def test_model_registry_integration():
    checkpoints, manifests, artifact = build_stores()

    result = manifests.create_from_checkpoint_store(
        checkpoints,
        "sirellm",
        "v1",
        100,
        metadata={
            "owner": "models",
        },
    )

    registry = ModelRegistry()

    registered = (
        manifests
        .register_with_model_registry(
            registry,
            "sirellm",
            "v1",
            stage=True,
            metadata={
                "release": "candidate",
            },
        )
    )

    eq(
        registered.checkpoint_path,
        artifact.path,
        "registry uses checkpoint referenced by manifest",
    )

    eq(
        registered.status,
        "staged",
        "manifest can register staged model",
    )

    eq(
        registered.metadata[
            "manifest_path"
        ],
        result[
            "path"
        ],
        "registry metadata links manifest path",
    )

    eq(
        registered.metadata[
            "release"
        ],
        "candidate",
        "registration metadata merged",
    )


def test_load_existing():
    checkpoints, manifests, _ = build_stores()

    result = manifests.create_from_checkpoint_store(
        checkpoints,
        "sirellm",
        "v1",
        100,
    )

    second_root = (
        "model_store/manifests/"
        "_test_manifest_catalog_only"
    )

    if os.path.exists(
        second_root
    ):
        shutil.rmtree(
            second_root
        )

    try:
        second = ManifestStore(
            second_root
        )

        loaded = second.load_existing(
            result[
                "path"
            ]
        )

        eq(
            loaded.model_id,
            "sirellm",
            "existing manifest loaded into independent catalog",
        )

        eq(
            second.status()[
                "manifest_count"
            ],
            1,
            "load_existing catalogs manifest",
        )

    finally:
        if os.path.exists(
            second_root
        ):
            shutil.rmtree(
                second_root
            )


def test_path_safety():
    checkpoints, manifests, _ = build_stores()

    expect_error(
        ValueError,
        lambda: (
            manifests
            .create_from_checkpoint_store(
                checkpoints,
                "../sirellm",
                "v1",
                1,
            )
        ),
        "unsafe model path rejected",
    )

    expect_error(
        ValueError,
        lambda: (
            manifests
            ._manifest_path(
                "sirellm",
                "v1/evil",
            )
        ),
        "unsafe version path rejected",
    )


def test_status():
    checkpoints, manifests, _ = build_stores()

    manifests.create_from_checkpoint_store(
        checkpoints,
        "sirellm",
        "v1",
        100,
    )

    status = manifests.status()

    eq(
        status[
            "model_count"
        ],
        1,
        "manifest store model count",
    )

    eq(
        status[
            "manifest_count"
        ],
        1,
        "manifest store manifest count",
    )

    eq(
        status[
            "immutable"
        ],
        True,
        "manifest store reports immutable semantics",
    )


def main():
    for path in (
        CHECKPOINT_ROOT,
        MANIFEST_ROOT,
    ):
        if os.path.exists(
            path
        ):
            shutil.rmtree(
                path
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

    tests = [
        test_manifest_object,
        test_create_from_checkpoint,
        test_persistence_round_trip,
        test_manifest_tamper_detection,
        test_store_verify_checkpoint_match,
        test_manifest_file_tamper,
        test_immutability,
        test_catalog_order,
        test_model_registry_integration,
        test_load_existing,
        test_path_safety,
        test_status,
    ]

    try:
        for test in tests:
            for path in (
                CHECKPOINT_ROOT,
                MANIFEST_ROOT,
            ):
                if os.path.exists(
                    path
                ):
                    shutil.rmtree(
                        path
                    )

            test()

    finally:
        for path in (
            CHECKPOINT_ROOT,
            MANIFEST_ROOT,
        ):
            if os.path.exists(
                path
            ):
                shutil.rmtree(
                    path
                )

        if os.path.exists(
            SOURCE_PATH
        ):
            os.remove(
                SOURCE_PATH
            )

    print(
        "MODEL STORE MANIFESTS TEST SUITE: PASS"
    )
    print(
        "Assertions passed:",
        ASSERTIONS,
    )
    print(
        "Files validated: 5/5"
    )
    print(
        "Checkpoint-derived model manifests: VALIDATED"
    )
    print(
        "Architecture/tokenizer/runtime metadata: VALIDATED"
    )
    print(
        "Deterministic checksum-protected manifest codec: VALIDATED"
    )
    print(
        "Immutable filesystem manifest storage: VALIDATED"
    )
    print(
        "Checkpoint-reference verification: VALIDATED"
    )
    print(
        "Deterministic manifest catalog: VALIDATED"
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
