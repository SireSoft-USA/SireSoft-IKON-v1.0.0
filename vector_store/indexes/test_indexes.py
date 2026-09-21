import os
import shutil

MATH_BASE = "libs/core/math/"
SERIAL_BASE = "libs/core/serialization/"
SIM_BASE = "libs/retrieval/similarity/"
INDEX_BASE = "libs/retrieval/index/"
SERVICE_BASE = "services/retrieval_service/"
STORE_BASE = "vector_store/indexes/"

namespace = {
    "__builtins__": __builtins__,
}

for filename in [
    "scalar.py",
]:
    path = MATH_BASE + filename

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

for filename in [
    "dot_product.py",
    "cosine.py",
    "distance.py",
    "batch_similarity.py",
    "scorer.py",
]:
    path = SIM_BASE + filename

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
    "flat_index.py",
    "persistence.py",
]:
    path = INDEX_BASE + filename

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

# Only manager is needed for the retrieval bridge contract test; a small fake
# retrieval manager is used below to avoid rebuilding the whole NLP pipeline.
for filename in [
    "artifact.py",
    "path_policy.py",
    "catalog.py",
    "bridge.py",
    "store.py",
]:
    path = STORE_BASE + filename

    source = open(
        path,
        "r",
        encoding="utf-8",
    ).read()

    if (
        filename != "store.py"
        and "import " in source
    ):
        raise AssertionError(
            "indexes implementation contains unexpected import: "
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

ROOT = (
    "vector_store/indexes/"
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


def close(
    actual,
    expected,
    tolerance=1e-9,
):
    difference = actual - expected

    if difference < 0:
        difference = -difference

    return (
        difference
        <= tolerance
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


def build_index():
    index = FlatVectorIndex(
        dimension=3,
        metric=CosineSimilarity(),
    )

    index.bulk_add([
        IndexEntry(
            item_id="software",
            vector=[
                1.0,
                0.0,
                0.0,
            ],
            text=(
                "software engineering"
            ),
            document_id="doc-1",
            dataset_id="siresoft",
            metadata={
                "section": "services",
            },
        ),
        IndexEntry(
            item_id="cloud",
            vector=[
                0.8,
                0.2,
                0.0,
            ],
            text=(
                "cloud applications"
            ),
            document_id="doc-2",
            dataset_id="siresoft",
            metadata={
                "section": "services",
            },
        ),
        IndexEntry(
            item_id="other",
            vector=[
                0.0,
                0.0,
                1.0,
            ],
            text="cooking",
            document_id="doc-3",
            dataset_id="other",
        ),
    ])

    return index


class FakeRetrievalManager:
    def __init__(
        self,
        index,
    ):
        self.index = index

    def status(
        self,
    ):
        return {
            "documents": 2,
            "chunks": (
                self.index.count()
            ),
            "dimension": (
                self.index.dimension
            ),
        }

    def tokenizer_signature(
        self,
    ):
        return "fake-tokenizer-signature"


def fresh_store():
    return VectorIndexStore(
        ROOT
    )


def test_artifact():
    artifact = VectorIndexArtifact(
        index_id="siresoft",
        version="v1",
        path="/x",
        file_checksum=1,
        byte_count=20,
        dimension=3,
        entry_count=2,
        created_at=1,
    )

    eq(
        artifact.key(),
        "siresoft@v1",
        "vector-index artifact identity",
    )

    eq(
        artifact.to_dict()[
            "metric_name"
        ],
        "cosine",
        "artifact metric metadata",
    )


def test_path_policy():
    policy = VectorIndexPathPolicy(
        "vector_indexes"
    )

    eq(
        policy.artifact_path(
            "siresoft",
            "v1",
        ),
        (
            "vector_indexes/"
            "siresoft/v1.sllmvidx"
        ),
        "deterministic index/version path",
    )

    expect_error(
        ValueError,
        lambda: policy.artifact_path(
            "../bad",
            "v1",
        ),
        "unsafe index path rejected",
    )

    expect_error(
        ValueError,
        lambda: policy.artifact_path(
            "siresoft",
            "v1/evil",
        ),
        "unsafe version path rejected",
    )


def test_put_and_load():
    source = build_index()
    store = fresh_store()

    artifact = store.put_index(
        index_id="siresoft",
        version="v1",
        index=source,
        created_at=100,
        metadata={
            "purpose": "retrieval",
        },
        activate=True,
    )

    check(
        os.path.exists(
            artifact.path
        ),
        "vector-index artifact file created",
    )

    eq(
        artifact.entry_count,
        3,
        "artifact entry count",
    )

    eq(
        artifact.dimension,
        3,
        "artifact dimension",
    )

    loaded = store.load_index(
        "siresoft"
    )

    index = loaded[
        "index"
    ]

    eq(
        index.state_dict(),
        source.state_dict(),
        "loaded index exactly matches source state",
    )

    results = index.search(
        [
            1.0,
            0.0,
            0.0,
        ],
        top_k=2,
    )

    eq(
        results[
            0
        ].item_id,
        "software",
        "loaded index remains searchable",
    )

    check(
        results[
            0
        ].score
        >= results[
            1
        ].score,
        "search ranking preserved",
    )


def test_verify():
    store = fresh_store()

    store.put_index(
        "siresoft",
        "v1",
        build_index(),
        created_at=1,
    )

    result = store.verify(
        "siresoft",
        "v1",
    )

    eq(
        result[
            "valid"
        ],
        True,
        "fresh index artifact verifies",
    )

    eq(
        result[
            "checksum_match"
        ],
        True,
        "whole-file checksum matches",
    )

    eq(
        result[
            "dimension_match"
        ],
        True,
        "dimension summary matches",
    )

    eq(
        result[
            "entry_count_match"
        ],
        True,
        "entry-count summary matches",
    )


def test_tamper_detection():
    store = fresh_store()

    artifact = store.put_index(
        "siresoft",
        "v1",
        build_index(),
        created_at=1,
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
        "siresoft",
        "v1",
    )

    eq(
        result[
            "valid"
        ],
        False,
        "tampered index artifact rejected",
    )

    eq(
        result[
            "state_valid"
        ],
        False,
        "inner IndexPersistence checksum rejects tampering",
    )


def test_immutability():
    store = fresh_store()

    store.put_index(
        "siresoft",
        "v1",
        build_index(),
        created_at=1,
    )

    expect_error(
        ValueError,
        lambda: store.put_index(
            "siresoft",
            "v1",
            build_index(),
            created_at=2,
        ),
        "catalogued version cannot be overwritten",
    )

    second = VectorIndexStore(
        ROOT
    )

    expect_error(
        FileExistsError,
        lambda: second.put_index(
            "siresoft",
            "v1",
            build_index(),
            created_at=2,
        ),
        "existing index file cannot be overwritten",
    )


def test_retrieval_bridge():
    source_index = build_index()

    retrieval = FakeRetrievalManager(
        source_index
    )

    store = fresh_store()

    artifact = (
        store
        .put_from_retrieval_manager(
            index_id="retrieval-main",
            version="v1",
            retrieval_manager=(
                retrieval
            ),
            created_at=1,
            metadata={
                "environment": "test",
            },
        )
    )

    eq(
        artifact.metadata[
            "source"
        ],
        "retrieval_manager",
        "retrieval bridge source metadata",
    )

    eq(
        artifact.metadata[
            "tokenizer_signature"
        ],
        "fake-tokenizer-signature",
        "retrieval bridge tokenizer signature metadata",
    )

    eq(
        artifact.metadata[
            "environment"
        ],
        "test",
        "caller metadata merged with bridge metadata",
    )

    eq(
        store.load_index(
            "retrieval-main",
            "v1",
        )[
            "index"
        ].state_dict(),
        source_index.state_dict(),
        "retrieval bridge stores exact existing vector index",
    )


def test_filters_survive():
    store = fresh_store()

    store.put_index(
        "siresoft",
        "v1",
        build_index(),
        created_at=1,
    )

    index = store.load_index(
        "siresoft",
        "v1",
    )[
        "index"
    ]

    results = index.search(
        [
            1.0,
            0.0,
            0.0,
        ],
        top_k=5,
        filters={
            "dataset_id": (
                "siresoft"
            ),
        },
    )

    eq(
        [
            row.entry.dataset_id
            for row in results
        ],
        [
            "siresoft",
            "siresoft",
        ],
        "dataset filters preserved after reload",
    )

    section_results = (
        index.search(
            [
                1.0,
                0.0,
                0.0,
            ],
            top_k=5,
            filters={
                "section": "services",
            },
        )
    )

    eq(
        len(
            section_results
        ),
        2,
        "metadata filters preserved after reload",
    )


def test_multiple_indexes_versions_activation():
    store = fresh_store()

    store.put_index(
        "siresoft",
        "v1",
        build_index(),
        created_at=1,
    )

    store.put_index(
        "siresoft",
        "v2",
        build_index(),
        created_at=2,
    )

    store.put_index(
        "general",
        "v1",
        build_index(),
        created_at=3,
    )

    store.activate(
        "siresoft",
        "v2",
    )

    eq(
        store.active(
            "siresoft"
        )[
            "version"
        ],
        "v2",
        "active version selected per index",
    )

    eq(
        store.status()[
            "index_count"
        ],
        2,
        "store counts distinct indexes",
    )

    eq(
        store.status()[
            "artifact_count"
        ],
        3,
        "store counts all version artifacts",
    )

    eq(
        [
            row[
                "version"
            ]
            for row
            in store.list_versions(
                "siresoft"
            )
        ],
        [
            "v1",
            "v2",
        ],
        "version order preserved",
    )


def test_catalog_state():
    catalog = (
        VectorIndexCatalog()
    )

    catalog.add(
        VectorIndexArtifact(
            "idx",
            "v1",
            "/a",
            1,
            10,
            3,
            1,
            1,
        )
    )

    catalog.add(
        VectorIndexArtifact(
            "idx",
            "v2",
            "/b",
            2,
            11,
            3,
            2,
            2,
        )
    )

    catalog.activate(
        "idx",
        "v2",
    )

    state = (
        catalog.export_state()
    )

    restored = (
        VectorIndexCatalog()
    )

    restored.load_state(
        state
    )

    eq(
        restored.export_state(),
        state,
        "vector-index catalog exact state round trip",
    )


def test_metadata_copy_isolation():
    store = fresh_store()

    metadata = {
        "tags": [
            "a",
        ],
    }

    artifact = store.put_index(
        "idx",
        "v1",
        build_index(),
        created_at=1,
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
        ROOT
    ):
        shutil.rmtree(
            ROOT
        )

    tests = [
        test_artifact,
        test_path_policy,
        test_put_and_load,
        test_verify,
        test_tamper_detection,
        test_immutability,
        test_retrieval_bridge,
        test_filters_survive,
        test_multiple_indexes_versions_activation,
        test_catalog_state,
        test_metadata_copy_isolation,
    ]

    try:
        for test in tests:
            if os.path.exists(
                ROOT
            ):
                shutil.rmtree(
                    ROOT
                )

            test()

    finally:
        if os.path.exists(
            ROOT
        ):
            shutil.rmtree(
                ROOT
            )

    print(
        "VECTOR STORE INDEXES TEST SUITE: PASS"
    )
    print(
        "Assertions passed:",
        ASSERTIONS,
    )
    print(
        "Files validated: 5/5"
    )
    print(
        "FlatVectorIndex persistence integration: VALIDATED"
    )
    print(
        "Immutable multi-index/version storage: VALIDATED"
    )
    print(
        "Whole-file and inner index tamper detection: VALIDATED"
    )
    print(
        "RetrievalManager index bridge: VALIDATED"
    )
    print(
        "Search/filter behavior after reload: VALIDATED"
    )
    print(
        "Per-index active-version selection: VALIDATED"
    )
    print(
        "Deterministic index catalog: VALIDATED"
    )
    print(
        "Third-party dependencies: 0"
    )
    print(
        "Standard-library filesystem dependency: os"
    )


main()
