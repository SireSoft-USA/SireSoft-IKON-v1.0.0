import os
import shutil

MATH_BASE = "libs/core/math/"
SERIAL_BASE = "libs/core/serialization/"
TOKENIZER_BASE = "libs/nlp/tokenizer/"
CORPUS_BASE = "libs/nlp/corpus/"
CHUNK_BASE = "libs/retrieval/chunking/"
EMBED_BASE = "libs/retrieval/embedding/"
SIM_BASE = "libs/retrieval/similarity/"
INDEX_BASE = "libs/retrieval/index/"
RANK_BASE = "libs/retrieval/ranking/"
SERVICE_BASE = "services/retrieval_service/"
STORE_BASE = "vector_store/siresoft/"

namespace = {
    "__builtins__": __builtins__,
}

groups = [
    (
        MATH_BASE,
        [
            "scalar.py",
        ],
    ),
    (
        SERIAL_BASE,
        [
            "binary_writer.py",
            "binary_reader.py",
            "checksum.py",
        ],
    ),
    (
        TOKENIZER_BASE,
        [
            "special_tokens.py",
            "byte_encoder.py",
            "pair_counter.py",
            "vocabulary.py",
            "bpe_trainer.py",
            "bpe_tokenizer.py",
        ],
    ),
    (
        CORPUS_BASE,
        [
            "document.py",
        ],
    ),
    (
        CHUNK_BASE,
        [
            "chunk.py",
            "boundaries.py",
            "document_chunker.py",
        ],
    ),
    (
        EMBED_BASE,
        [
            "hash_features.py",
            "idf.py",
            "embedder.py",
        ],
    ),
    (
        SIM_BASE,
        [
            "dot_product.py",
            "cosine.py",
            "distance.py",
            "batch_similarity.py",
            "scorer.py",
        ],
    ),
    (
        INDEX_BASE,
        [
            "entry.py",
            "flat_index.py",
            "persistence.py",
        ],
    ),
    (
        RANK_BASE,
        [
            "result.py",
            "dedup.py",
            "reranker.py",
            "mmr.py",
            "pipeline.py",
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
    "document_store.py",
    "result.py",
    "persistence.py",
    "manager.py",
]:
    path = SERVICE_BASE + filename

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
    "snapshot.py",
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

ROOT = (
    "vector_store/siresoft/"
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


def build_tokenizer(
    variant=1,
):
    encoder = ByteEncoder()
    specials = SpecialTokens()

    if variant == 1:
        corpus = [
            (
                "SireSoft software engineering "
                "custom applications business systems"
            ),
            (
                "web development mobile development "
                "cloud systems artificial intelligence"
            ),
            (
                "professional technology services "
                "client software projects"
            ),
        ]
    else:
        corpus = [
            (
                "cooking recipes travel music cinema"
            ),
            (
                "completely different tokenizer vocabulary"
            ),
        ]

    model = (
        BPETrainer(
            byte_encoder=encoder,
            pair_counter=PairCounter(),
            vocabulary_factory=Vocabulary,
            special_tokens=specials,
        )
        .train(
            corpus,
            vocab_size=300,
            min_frequency=2,
        )
    )

    return BPETokenizer(
        model,
        encoder,
        specials,
    )


def documents():
    return [
        {
            "document_id": (
                "siresoft-company"
            ),
            "dataset_id": (
                "siresoft"
            ),
            "text": (
                "SireSoft provides professional "
                "software engineering and custom "
                "application development services "
                "for business clients."
            ),
            "metadata": {
                "section": "company",
            },
            "provenance": {
                "source_file": (
                    "datasets/raw/siresoft/"
                    "siresoft.txt"
                ),
            },
        },
        {
            "document_id": (
                "siresoft-services"
            ),
            "dataset_id": (
                "siresoft"
            ),
            "text": (
                "SireSoft builds web, mobile, "
                "cloud and artificial intelligence "
                "software systems."
            ),
            "metadata": {
                "section": "services",
            },
            "provenance": {
                "source_file": (
                    "datasets/raw/siresoft/"
                    "siresoft.txt"
                ),
            },
        },
    ]


def build_manager(
    tokenizer=None,
):
    if tokenizer is None:
        tokenizer = (
            build_tokenizer()
        )

    manager = RetrievalManager(
        tokenizer=tokenizer,
        Document=Document,
        dimension=256,
        min_n=1,
        max_n=2,
        max_chars=1000,
        overlap_chars=0,
        min_chunk_chars=0,
    )

    manager.index_documents(
        documents(),
        mode="replace",
        refit=True,
    )

    return manager


def fresh_store():
    return SireSoftVectorStore(
        ROOT
    )


def test_snapshot_descriptor():
    snapshot = SireSoftVectorSnapshot(
        version="v1",
        path="/x",
        file_checksum=123,
        byte_count=50,
        created_at=1,
        documents=2,
        chunks=2,
        index_entries=2,
        dimension=256,
        tokenizer_signature="abc",
    )

    eq(
        snapshot.key(),
        "siresoft@v1",
        "snapshot identity key",
    )

    eq(
        snapshot.to_dict()[
            "collection_id"
        ],
        "siresoft",
        "snapshot collection locked to siresoft",
    )


def test_path_policy():
    policy = SireSoftVectorPathPolicy(
        "vector_data"
    )

    eq(
        policy.snapshot_path(
            "2026-09-18"
        ),
        (
            "vector_data/"
            "2026-09-18.slretr"
        ),
        "deterministic SireSoft vector snapshot path",
    )

    expect_error(
        ValueError,
        lambda: policy.snapshot_path(
            "../evil"
        ),
        "path traversal rejected",
    )


def test_put_real_retrieval_snapshot():
    manager = build_manager()
    store = fresh_store()

    snapshot = store.put(
        version="v1",
        retrieval_manager=manager,
        created_at=100,
        metadata={
            "source": (
                "datasets/raw/siresoft/"
                "siresoft.txt"
            ),
        },
        activate=True,
    )

    check(
        os.path.exists(
            snapshot.path
        ),
        "retrieval snapshot stored",
    )

    eq(
        snapshot.documents,
        2,
        "snapshot records real retrieval document count",
    )

    eq(
        snapshot.index_entries,
        2,
        "snapshot records real vector index entries",
    )

    eq(
        snapshot.tokenizer_signature,
        manager.tokenizer_signature(),
        "snapshot records tokenizer compatibility signature",
    )

    eq(
        store.active()[
            "version"
        ],
        "v1",
        "stored version activated",
    )


def test_state_round_trip_exact():
    manager = build_manager()
    before = manager.export_state()

    store = fresh_store()

    snapshot = store.put(
        "v1",
        manager,
        created_at=1,
    )

    observed = (
        manager.persistence
        .read_state(
            snapshot.path
        )
    )

    eq(
        observed,
        before,
        "stored SireSoft snapshot exactly preserves retrieval state",
    )


def test_verify():
    manager = build_manager()
    store = fresh_store()

    store.put(
        "v1",
        manager,
        created_at=1,
    )

    result = store.verify(
        "v1",
        retrieval_manager=manager,
    )

    eq(
        result[
            "valid"
        ],
        True,
        "fresh SireSoft vector snapshot verifies",
    )

    eq(
        result[
            "file_checksum_match"
        ],
        True,
        "whole-file checksum matches",
    )

    eq(
        result[
            "tokenizer_compatible"
        ],
        True,
        "compatible tokenizer recognized",
    )

    eq(
        result[
            "summary_match"
        ],
        True,
        "snapshot summary matches retrieval state",
    )


def test_tamper_detection():
    manager = build_manager()
    store = fresh_store()

    snapshot = store.put(
        "v1",
        manager,
        created_at=1,
    )

    handle = open(
        snapshot.path,
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
        snapshot.path,
        "wb",
    )

    try:
        handle.write(
            data
        )
    finally:
        handle.close()

    result = store.verify(
        "v1",
        retrieval_manager=manager,
    )

    eq(
        result[
            "valid"
        ],
        False,
        "tampered vector snapshot rejected",
    )

    eq(
        result[
            "retrieval_snapshot_valid"
        ],
        False,
        "inner retrieval checksum rejects tampering",
    )


def test_immutable_version():
    manager = build_manager()
    store = fresh_store()

    store.put(
        "v1",
        manager,
        created_at=1,
    )

    expect_error(
        ValueError,
        lambda: store.put(
            "v1",
            manager,
            created_at=2,
        ),
        "catalogued version cannot be overwritten",
    )

    second = SireSoftVectorStore(
        ROOT
    )

    expect_error(
        FileExistsError,
        lambda: second.put(
            "v1",
            manager,
            created_at=2,
        ),
        "existing immutable snapshot file cannot be overwritten",
    )


def test_reject_non_siresoft_dataset():
    manager = build_manager()

    mixed = documents()

    mixed.append({
        "document_id": "general",
        "dataset_id": "general",
        "text": "unrelated general corpus",
    })

    manager.index_documents(
        mixed,
        mode="replace",
        refit=True,
    )

    store = fresh_store()

    expect_error(
        ValueError,
        lambda: store.put(
            "v1",
            manager,
            created_at=1,
        ),
        "SireSoft vector store rejects non-siresoft documents",
    )


def test_load_into_real_retrieval_manager():
    tokenizer = build_tokenizer()

    source = build_manager(
        tokenizer=tokenizer
    )

    store = fresh_store()

    store.put(
        "v1",
        source,
        created_at=1,
        activate=True,
    )

    target = RetrievalManager(
        tokenizer=tokenizer,
        Document=Document,
        dimension=256,
        min_n=1,
        max_n=2,
        max_chars=1000,
        overlap_chars=0,
        min_chunk_chars=0,
    )

    result = store.load_into(
        target
    )

    eq(
        result[
            "retrieval_status"
        ][
            "documents"
        ],
        2,
        "active snapshot loads into real retrieval manager",
    )

    eq(
        target.export_state(),
        source.export_state(),
        "loaded retrieval manager matches source state",
    )

    search = target.search(
        (
            "software engineering custom "
            "application development"
        ),
        top_k=1,
        use_mmr=False,
    )

    eq(
        search.hits[
            0
        ].document_id,
        "siresoft-company",
        "loaded store remains searchable",
    )


def test_tokenizer_mismatch_rejected():
    source = build_manager(
        tokenizer=(
            build_tokenizer(
                variant=1
            )
        )
    )

    store = fresh_store()

    store.put(
        "v1",
        source,
        created_at=1,
    )

    incompatible = RetrievalManager(
        tokenizer=(
            build_tokenizer(
                variant=2
            )
        ),
        Document=Document,
        dimension=256,
        min_n=1,
        max_n=2,
        max_chars=1000,
        overlap_chars=0,
        min_chunk_chars=0,
    )

    verification = store.verify(
        "v1",
        retrieval_manager=(
            incompatible
        ),
    )

    eq(
        verification[
            "valid"
        ],
        False,
        "snapshot with different tokenizer is not runtime-compatible",
    )

    eq(
        verification[
            "tokenizer_compatible"
        ],
        False,
        "tokenizer mismatch explicitly reported",
    )

    expect_error(
        ValueError,
        lambda: store.load_into(
            incompatible,
            "v1",
        ),
        "incompatible snapshot cannot be loaded",
    )


def test_multiple_versions_and_activation():
    manager = build_manager()
    store = fresh_store()

    store.put(
        "v1",
        manager,
        created_at=1,
    )

    store.put(
        "v2",
        manager,
        created_at=2,
    )

    eq(
        [
            item[
                "version"
            ]
            for item
            in store.list_snapshots()
        ],
        [
            "v1",
            "v2",
        ],
        "version catalog preserves insertion order",
    )

    store.activate(
        "v2"
    )

    eq(
        store.active()[
            "version"
        ],
        "v2",
        "explicit active version selection",
    )

    eq(
        store.status()[
            "snapshot_count"
        ],
        2,
        "store snapshot count",
    )


def test_catalog_state():
    catalog = SireSoftVectorCatalog()

    catalog.add(
        SireSoftVectorSnapshot(
            "v1",
            "/x",
            1,
            10,
            1,
            1,
            1,
            1,
            8,
            "tok",
        )
    )

    catalog.activate(
        "v1"
    )

    state = catalog.export_state()

    restored = (
        SireSoftVectorCatalog()
    )

    restored.load_state(
        state
    )

    eq(
        restored.export_state(),
        state,
        "catalog exact state round trip",
    )


def main():
    if os.path.exists(
        ROOT
    ):
        shutil.rmtree(
            ROOT
        )

    tests = [
        test_snapshot_descriptor,
        test_path_policy,
        test_put_real_retrieval_snapshot,
        test_state_round_trip_exact,
        test_verify,
        test_tamper_detection,
        test_immutable_version,
        test_reject_non_siresoft_dataset,
        test_load_into_real_retrieval_manager,
        test_tokenizer_mismatch_rejected,
        test_multiple_versions_and_activation,
        test_catalog_state,
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
        "SIRESOFT VECTOR STORE TEST SUITE: PASS"
    )
    print(
        "Assertions passed:",
        ASSERTIONS,
    )
    print(
        "Files validated: 4/4"
    )
    print(
        "Real RetrievalManager snapshot integration: VALIDATED"
    )
    print(
        "SireSoft-only dataset boundary: VALIDATED"
    )
    print(
        "Immutable versioned retrieval snapshots: VALIDATED"
    )
    print(
        "Tokenizer compatibility enforcement: VALIDATED"
    )
    print(
        "Whole-file and inner snapshot tamper detection: VALIDATED"
    )
    print(
        "Active-version loading/searchability: VALIDATED"
    )
    print(
        "Deterministic snapshot catalog: VALIDATED"
    )
    print(
        "Third-party dependencies: 0"
    )
    print(
        "Standard-library filesystem dependency: os"
    )


main()
