MATH_BASE = "libs/core/math/"
SERIAL_BASE = "libs/core/serialization/"
TOKENIZER_BASE = "libs/nlp/tokenizer/"
CHUNK_BASE = "libs/retrieval/chunking/"
EMBED_BASE = "libs/retrieval/embedding/"
SIM_BASE = "libs/retrieval/similarity/"
INDEX_BASE = "libs/retrieval/index/"

namespace = {
    "__builtins__": __builtins__,
}

# Handwritten scalar math.
path = MATH_BASE + "scalar.py"
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

# Core binary persistence.
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

# Real tokenizer.
for filename in [
    "special_tokens.py",
    "byte_encoder.py",
    "pair_counter.py",
    "vocabulary.py",
    "bpe_trainer.py",
    "bpe_tokenizer.py",
]:
    path = TOKENIZER_BASE + filename

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

# Retrieval chunk.
path = CHUNK_BASE + "chunk.py"
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

# Real embedding.
for filename in [
    "hash_features.py",
    "idf.py",
    "embedder.py",
]:
    path = EMBED_BASE + filename

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

# Similarity stack needed for real retrieval.
for filename in [
    "cosine.py",
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

# New index implementation.
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

    if "import " in source:
        raise AssertionError(
            "index implementation contains forbidden import: "
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
        raise AssertionError(
            message
        )


def eq(actual, expected, message):
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
    tolerance=1e-8,
):
    difference = (
        actual - expected
    )

    if difference < 0:
        difference = -difference

    return (
        difference <= tolerance
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

    except Exception as exc:
        raise AssertionError(
            message
            + " | wrong exception="
            + repr(exc)
        )

    raise AssertionError(
        message
        + " | expected exception was not raised"
    )


def build_tokenizer():
    byte_encoder = ByteEncoder()
    specials = SpecialTokens()

    model = BPETrainer(
        byte_encoder=byte_encoder,
        pair_counter=PairCounter(),
        vocabulary_factory=Vocabulary,
        special_tokens=specials,
    ).train(
        [
            "SireSoft software engineering services.",
            "web development cloud applications.",
            "artificial intelligence machine learning.",
            "professional client software projects.",
            "cooking vegetables kitchen recipes.",
            "travel mountains hiking rivers.",
            "اردو software engineering.",
        ],
        vocab_size=320,
        min_frequency=2,
    )

    return BPETokenizer(
        model,
        byte_encoder,
        specials,
    )


def build_real_retrieval():
    tokenizer = build_tokenizer()

    chunks = [
        Chunk(
            chunk_id="sire-software",
            document_id="siresoft-main",
            dataset_id="siresoft",
            text=(
                "SireSoft provides professional software "
                "engineering and application development services."
            ),
            chunk_index=0,
            metadata={
                "section": "services",
                "rag": True,
            },
            provenance={
                "file": "siresoft.txt",
            },
        ),
        Chunk(
            chunk_id="sire-ai",
            document_id="siresoft-main",
            dataset_id="siresoft",
            text=(
                "SireSoft works on artificial intelligence "
                "and machine learning solutions."
            ),
            chunk_index=1,
            metadata={
                "section": "ai",
                "rag": True,
            },
            provenance={
                "file": "siresoft.txt",
            },
        ),
        Chunk(
            chunk_id="other-food",
            document_id="other",
            dataset_id="other",
            text=(
                "Cooking vegetables and kitchen recipes "
                "for dinner."
            ),
            chunk_index=0,
            metadata={
                "section": "food",
                "rag": False,
            },
        ),
    ]

    embedder = HashingTFIDFEmbedder(
        tokenizer=tokenizer,
        dimension=1024,
        min_n=1,
        max_n=2,
    )

    embedder.fit_chunks(
        chunks
    )

    scorer = SimilarityScorer(
        embedder
    )

    embedded = scorer.embed_items(
        chunks
    )

    index = FlatVectorIndex(
        dimension=1024,
        metric=CosineSimilarity(),
    )

    for item in embedded:
        index.add_embedded(
            item
        )

    return (
        embedder,
        chunks,
        index,
    )


def test_entry_copy_and_identity():
    source_vector = [
        1.0,
        2.0,
    ]

    entry = IndexEntry(
        item_id="x",
        vector=source_vector,
        text="hello",
        document_id="doc",
        dataset_id="set",
        metadata={
            "kind": "test",
        },
    )

    source_vector[0] = 99.0

    eq(
        entry.vector,
        [1.0, 2.0],
        "entry copies caller vector",
    )

    eq(
        entry.dimension(),
        2,
        "entry dimension",
    )

    eq(
        entry.metadata["kind"],
        "test",
        "entry metadata",
    )


def test_add_get_remove():
    index = FlatVectorIndex(
        dimension=2
    )

    first = IndexEntry(
        "a",
        [1.0, 0.0],
    )

    second = IndexEntry(
        "b",
        [0.0, 1.0],
    )

    index.add(
        first
    ).add(
        second
    )

    eq(
        index.count(),
        2,
        "index count after adds",
    )

    eq(
        index.ids(),
        ["a", "b"],
        "stable insertion order",
    )

    check(
        index.contains("a"),
        "index contains item",
    )

    eq(
        index.get("a").item_id,
        "a",
        "index get",
    )

    removed = index.remove(
        "a"
    )

    eq(
        removed.item_id,
        "a",
        "remove returns entry",
    )

    eq(
        index.ids(),
        ["b"],
        "remove updates order",
    )


def test_upsert_preserves_order():
    index = FlatVectorIndex(
        dimension=2
    )

    index.bulk_add(
        [
            IndexEntry(
                "a",
                [1.0, 0.0],
            ),
            IndexEntry(
                "b",
                [0.0, 1.0],
            ),
        ]
    )

    index.upsert(
        IndexEntry(
            "a",
            [0.5, 0.5],
            text="updated",
        )
    )

    eq(
        index.ids(),
        ["a", "b"],
        "upsert preserves existing position",
    )

    eq(
        index.get("a").text,
        "updated",
        "upsert replaces content",
    )

    index.upsert(
        IndexEntry(
            "c",
            [1.0, 1.0],
        )
    )

    eq(
        index.ids(),
        ["a", "b", "c"],
        "new upsert appends",
    )


def test_bulk_add_transaction():
    index = FlatVectorIndex(
        dimension=2
    )

    index.add(
        IndexEntry(
            "existing",
            [1.0, 0.0],
        )
    )

    expect_error(
        ValueError,
        lambda: index.bulk_add(
            [
                IndexEntry(
                    "new",
                    [0.5, 0.5],
                ),
                IndexEntry(
                    "existing",
                    [0.0, 1.0],
                ),
            ]
        ),
        "bulk duplicate rejected",
    )

    eq(
        index.ids(),
        ["existing"],
        "failed bulk add does not partially mutate index",
    )


def test_exact_search():
    index = FlatVectorIndex(
        dimension=2
    )

    index.bulk_add(
        [
            IndexEntry(
                "best",
                [1.0, 0.0],
            ),
            IndexEntry(
                "medium",
                [0.8, 0.2],
            ),
            IndexEntry(
                "bad",
                [0.0, 1.0],
            ),
        ]
    )

    results = index.search(
        [1.0, 0.0],
        top_k=3,
    )

    eq(
        [
            result.item_id
            for result in results
        ],
        [
            "best",
            "medium",
            "bad",
        ],
        "exact index ranking",
    )

    eq(
        [
            result.rank
            for result in results
        ],
        [1, 2, 3],
        "index search ranks",
    )

    check(
        close(
            results[0].score,
            1.0,
        ),
        "top cosine score",
    )


def test_search_filters():
    index = FlatVectorIndex(
        dimension=2
    )

    index.bulk_add(
        [
            IndexEntry(
                "sire-service",
                [1.0, 0.0],
                dataset_id="siresoft",
                metadata={
                    "section": "services",
                },
            ),
            IndexEntry(
                "sire-ai",
                [0.9, 0.1],
                dataset_id="siresoft",
                metadata={
                    "section": "ai",
                },
            ),
            IndexEntry(
                "other",
                [1.0, 0.0],
                dataset_id="other",
                metadata={
                    "section": "services",
                },
            ),
        ]
    )

    filtered = index.search(
        [1.0, 0.0],
        top_k=5,
        filters={
            "dataset_id": "siresoft",
            "section": "services",
        },
    )

    eq(
        len(filtered),
        1,
        "filters reduce result set",
    )

    eq(
        filtered[0].item_id,
        "sire-service",
        "dataset + metadata filter",
    )


def test_threshold():
    index = FlatVectorIndex(
        dimension=2
    )

    index.bulk_add(
        [
            IndexEntry(
                "same",
                [1.0, 0.0],
            ),
            IndexEntry(
                "orthogonal",
                [0.0, 1.0],
            ),
        ]
    )

    results = index.search(
        [1.0, 0.0],
        top_k=10,
        min_score=0.5,
    )

    eq(
        [
            result.item_id
            for result in results
        ],
        ["same"],
        "minimum score filter",
    )


def test_real_sirellm_index_query():
    embedder, chunks, index = (
        build_real_retrieval()
    )

    query = embedder.embed_text(
        "software engineering services"
    )

    results = index.search(
        query,
        top_k=3,
    )

    eq(
        results[0].item_id,
        "sire-software",
        "real SireLLM RAG index ranks relevant chunk first",
    )

    check(
        results[0].score
        > results[-1].score,
        "relevant score above unrelated result",
    )

    eq(
        results[0].entry.provenance["file"],
        "siresoft.txt",
        "index preserves retrieval provenance",
    )

    eq(
        results[0].entry.dataset_id,
        "siresoft",
        "index preserves dataset identity",
    )


def test_real_filtered_siresoft_query():
    embedder, chunks, index = (
        build_real_retrieval()
    )

    query = embedder.embed_text(
        "software"
    )

    results = index.search(
        query,
        top_k=10,
        filters={
            "dataset_id": "siresoft",
            "rag": True,
        },
    )

    check(
        len(results) >= 1,
        "filtered SireSoft results returned",
    )

    for result in results:
        eq(
            result.entry.dataset_id,
            "siresoft",
            "filtered result dataset",
        )

        eq(
            result.entry.metadata["rag"],
            True,
            "filtered result RAG eligibility",
        )


def test_state_round_trip():
    index = FlatVectorIndex(
        dimension=3
    )

    index.bulk_add(
        [
            IndexEntry(
                "a",
                [1.0, 2.0, 3.0],
                text="alpha",
                dataset_id="x",
                metadata={
                    "number": 1,
                    "flag": True,
                },
            ),
            IndexEntry(
                "b",
                [4.0, 5.0, 6.0],
                text="beta",
                document_id="doc-b",
                provenance={
                    "source": "file.txt",
                },
            ),
        ]
    )

    restored = FlatVectorIndex(
        dimension=3
    )

    restored.load_state_dict(
        index.state_dict()
    )

    eq(
        restored.state_dict(),
        index.state_dict(),
        "in-memory state round trip",
    )


def test_binary_persistence():
    path = (
        "libs/retrieval/index/"
        "_test_vector_index.sidx"
    )

    embedder, chunks, index = (
        build_real_retrieval()
    )

    persistence = IndexPersistence()

    info = persistence.save(
        path,
        index,
    )

    check(
        info["bytes"] > 0,
        "persistent index writes bytes",
    )

    eq(
        info["entries"],
        3,
        "persistent index entry count",
    )

    restored = persistence.load(
        path,
        metric=CosineSimilarity(),
    )

    eq(
        restored.state_dict(),
        index.state_dict(),
        "binary persistent state exact round trip",
    )

    query = embedder.embed_text(
        "artificial intelligence machine learning"
    )

    original_results = index.search(
        query,
        top_k=3,
    )

    restored_results = restored.search(
        query,
        top_k=3,
    )

    eq(
        [
            result.item_id
            for result in restored_results
        ],
        [
            result.item_id
            for result in original_results
        ],
        "restored index preserves ranking",
    )

    eq(
        restored_results[0].item_id,
        "sire-ai",
        "restored real index returns AI chunk",
    )


def test_corruption_detection():
    path = (
        "libs/retrieval/index/"
        "_test_corrupt_vector_index.sidx"
    )

    index = FlatVectorIndex(
        dimension=2
    )

    index.add(
        IndexEntry(
            "a",
            [1.0, 0.0],
        )
    )

    persistence = IndexPersistence()

    persistence.save(
        path,
        index,
    )

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

    data[-1] ^= 0x01

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

    expect_error(
        ValueError,
        lambda: persistence.load(
            path
        ),
        "checksum catches index corruption",
    )


def test_validation():
    expect_error(
        ValueError,
        lambda: FlatVectorIndex(
            dimension=0
        ),
        "invalid index dimension",
    )

    index = FlatVectorIndex(
        dimension=2
    )

    expect_error(
        ValueError,
        lambda: index.add(
            IndexEntry(
                "bad",
                [1.0],
            )
        ),
        "wrong entry dimension",
    )

    index.add(
        IndexEntry(
            "a",
            [1.0, 0.0],
        )
    )

    expect_error(
        ValueError,
        lambda: index.add(
            IndexEntry(
                "a",
                [0.0, 1.0],
            )
        ),
        "duplicate ID rejected",
    )

    expect_error(
        ValueError,
        lambda: index.search(
            [1.0],
        ),
        "wrong query dimension",
    )

    expect_error(
        KeyError,
        lambda: index.get(
            "missing"
        ),
        "missing item rejected",
    )


def main():
    test_entry_copy_and_identity()
    test_add_get_remove()
    test_upsert_preserves_order()
    test_bulk_add_transaction()
    test_exact_search()
    test_search_filters()
    test_threshold()
    test_real_sirellm_index_query()
    test_real_filtered_siresoft_query()
    test_state_round_trip()
    test_binary_persistence()
    test_corruption_detection()
    test_validation()

    print(
        "VECTOR INDEX TEST SUITE: PASS"
    )
    print(
        "Assertions passed:",
        ASSERTIONS,
    )
    print(
        "Files validated: 3/3"
    )
    print(
        "Add/upsert/remove semantics: VALIDATED"
    )
    print(
        "Transactional bulk insertion: VALIDATED"
    )
    print(
        "Exact cosine top-k search: VALIDATED"
    )
    print(
        "Dataset/metadata filtering: VALIDATED"
    )
    print(
        "Real SireLLM chunk retrieval: VALIDATED"
    )
    print(
        "Binary persistence round-trip: VALIDATED"
    )
    print(
        "Index corruption detection: VALIDATED"
    )
    print(
        "Third-party dependencies: 0"
    )


main()
