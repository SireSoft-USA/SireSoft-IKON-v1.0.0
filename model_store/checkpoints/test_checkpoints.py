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
    policy = CheckpointPathPolicy('model_store_data')
    # os.path.join uses the host platform's separator (\ on Windows, / on Linux).
    # Check the actual checkpoint path without enforcing Unix-only formatting.
    expected_checkpoint = os.path.join('model_store_data', 'sirellm', 'v1.lbckpt')
    expected_directory = os.path.join('model_store_data', 'sirellm')
    eq(policy.checkpoint_path('sirellm', 'v1'), expected_checkpoint, 'current checkpoint extension')
    eq(policy.model_directory('sirellm'), expected_directory, 'model directory')
    expect_error(ValueError, lambda: policy.checkpoint_path('../bad', 'v1'), 'reject model traversal')
    expect_error(ValueError, lambda: policy.checkpoint_path('m', 'v1/other'), 'reject version traversal')
    expect_error(ValueError, lambda: policy.segment('.', 'x'), 'reject dot segment')


def test_artifact():
    artifact = CheckpointArtifact('m', 'v1', '/x', 'abc', 10, 5, 2, {'dim': 2}, {'team': ['a']})
    eq(artifact.key(), 'm@v1', 'identity key')
    eq(artifact.to_dict()['parameter_count'], 5, 'parameter count')
    copy = artifact.to_dict()
    copy['metadata']['team'].append('b')
    eq(artifact.metadata['team'], ['a'], 'metadata deep copied')
    expect_error(ValueError, lambda: CheckpointArtifact('', 'v1', '/x', 'abc', 10, 5, 2), 'reject empty model')


def test_store():
    store = build_store()
    artifact = store.put('sirellm', 'v1', SOURCE_PATH, metadata={'team': 'core'})
    check(os.path.exists(artifact.path), 'checkpoint exists')
    check(artifact.path.endswith('.lbckpt'), 'uses current file extension')
    eq(artifact.parameter_count, 12, 'model parameter count inspected')
    eq(artifact.parameter_tensors, 2, 'model tensor count inspected')
    eq(artifact.architecture['hidden_size'], 2, 'architecture metadata')
    eq(artifact.metadata['team'], 'core', 'user metadata')
    with open(artifact.path, 'rb') as file:
        stored = file.read()
    with open(SOURCE_PATH, 'rb') as file:
        source = file.read()
    eq(stored, source, 'immutable byte-for-byte copy')
    eq(store.get('sirellm','v1').key(), artifact.key(), 'catalog lookup')
    eq(store.status()['checkpoint_count'], 1, 'store status')
    eq(store.verify('sirellm', 'v1')['valid'], True, 'checksum verification')
    expect_error(FileExistsError, lambda: store.put('sirellm','v1',SOURCE_PATH), 'reject duplicate destination')
    artifact2 = store.put('sirellm', 'v2', SOURCE_PATH)
    check(os.path.exists(artifact2.path), 'versioned checkpoint')
    eq(store.catalog.count(), 2, 'catalog count')
    eq(len(store.catalog.versions('sirellm')), 2, 'catalog versions')


def test_tamper_detection():
    store = build_store()
    artifact = store.put('sirellm', 'v1', SOURCE_PATH)
    with open(artifact.path, 'r+b') as stream:
        stream.seek(-1, os.SEEK_END)
        old = stream.read(1)
        stream.seek(-1, os.SEEK_END)
        stream.write(bytes([old[0] ^ 1]))
    eq(store.verify('sirellm', 'v1')['valid'], False, 'tampered checkpoint rejected')


def main():
    global ASSERTIONS
    if os.path.exists(TMP_ROOT):
        shutil.rmtree(TMP_ROOT)
    if os.path.exists(SOURCE_PATH):
        os.remove(SOURCE_PATH)
    make_checkpoint(SOURCE_PATH)
    try:
        for test in (test_path_policy, test_artifact, test_store, test_tamper_detection):
            if os.path.exists(TMP_ROOT):
                shutil.rmtree(TMP_ROOT)
            test()
    finally:
        if os.path.exists(TMP_ROOT):
            shutil.rmtree(TMP_ROOT)
        if os.path.exists(SOURCE_PATH):
            os.remove(SOURCE_PATH)
    print('MODEL STORE CHECKPOINTS CURRENT-API TEST SUITE: PASS')
    print('Assertions passed:', ASSERTIONS)


if __name__ == '__main__':
    main()
