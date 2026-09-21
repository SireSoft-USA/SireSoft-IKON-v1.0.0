MATH_BASE = "libs/core/math/"
TOKENIZER_BASE = "libs/nlp/tokenizer/"
CHUNK_BASE = "libs/retrieval/chunking/"
EMBED_BASE = "libs/retrieval/embedding/"
SIM_BASE = "libs/retrieval/similarity/"

namespace = {
    "__builtins__": __builtins__,
}

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

    if "import " in source:
        raise AssertionError(
            "similarity implementation contains forbidden import: "
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

    return difference <= tolerance


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
            "web application development software.",
            "artificial intelligence machine learning.",
            "cloud systems engineering clients.",
            "cooking recipes vegetables kitchen.",
            "travel mountains rivers hiking.",
            "اردو software services.",
        ],
        vocab_size=320,
        min_frequency=2,
    )

    return BPETokenizer(
        model,
        byte_encoder,
        specials,
    )


def build_embedder():
    tokenizer = build_tokenizer()

    embedder = HashingTFIDFEmbedder(
        tokenizer=tokenizer,
        dimension=1024,
        min_n=1,
        max_n=2,
    )

    embedder.fit(
        [
            "SireSoft provides software engineering services",
            "web application development for clients",
            "artificial intelligence machine learning solutions",
            "cloud software systems",
            "cooking vegetables and kitchen recipes",
            "travel mountains hiking adventure",
        ]
    )

    return embedder


def test_dot_product():
    metric = DotProduct()

    check(
        close(
            metric.score(
                [1.0, 2.0, 3.0],
                [4.0, 5.0, 6.0],
            ),
            32.0,
        ),
        "dot product known value",
    )

    check(
        close(
            metric.score(
                [1.0, 0.0],
                [0.0, 1.0],
            ),
            0.0,
        ),
        "orthogonal dot product",
    )


def test_cosine_similarity():
    metric = CosineSimilarity()

    check(
        close(
            metric.score(
                [1.0, 2.0, 3.0],
                [1.0, 2.0, 3.0],
            ),
            1.0,
        ),
        "cosine self similarity",
    )

    check(
        close(
            metric.score(
                [1.0, 0.0],
                [0.0, 1.0],
            ),
            0.0,
        ),
        "orthogonal cosine",
    )

    check(
        close(
            metric.score(
                [1.0, 0.0],
                [-1.0, 0.0],
            ),
            -1.0,
        ),
        "opposite cosine",
    )

    check(
        close(
            metric.score(
                [0.0, 0.0],
                [1.0, 2.0],
            ),
            0.0,
        ),
        "zero vector cosine policy",
    )


def test_distances():
    euclidean = EuclideanDistance()
    manhattan = ManhattanDistance()

    check(
        close(
            euclidean.distance(
                [0.0, 0.0],
                [3.0, 4.0],
            ),
            5.0,
        ),
        "Euclidean 3-4-5",
    )

    check(
        close(
            manhattan.distance(
                [1.0, 2.0],
                [4.0, -2.0],
            ),
            7.0,
        ),
        "Manhattan known value",
    )

    check(
        euclidean.similarity(
            [1.0, 1.0],
            [1.0, 1.0],
        )
        > euclidean.similarity(
            [1.0, 1.0],
            [10.0, 10.0],
        ),
        "distance similarity ordering",
    )


def test_embedding_result_support():
    embedder = build_embedder()

    first = embedder.embed_text(
        "software engineering"
    )

    second = embedder.embed_text(
        "software engineering"
    )

    check(
        close(
            CosineSimilarity().score(
                first,
                second,
            ),
            1.0,
            tolerance=1e-7,
        ),
        "metrics accept EmbeddingResult",
    )


def test_batch_similarity_ordering():
    batch = BatchSimilarity(
        CosineSimilarity()
    )

    candidates = [
        {
            "id": "medium",
            "vector": [0.8, 0.2],
        },
        {
            "id": "best",
            "vector": [1.0, 0.0],
        },
        {
            "id": "bad",
            "vector": [0.0, 1.0],
        },
    ]

    results = batch.compare(
        [1.0, 0.0],
        candidates,
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
        "batch similarity score ordering",
    )

    eq(
        [
            result.rank
            for result in results
        ],
        [1, 2, 3],
        "batch ranks assigned",
    )


def test_stable_tie_break():
    batch = BatchSimilarity()

    candidates = [
        {
            "id": "first",
            "vector": [1.0, 0.0],
        },
        {
            "id": "second",
            "vector": [1.0, 0.0],
        },
    ]

    results = batch.compare(
        [1.0, 0.0],
        candidates,
    )

    eq(
        results[0].item_id,
        "first",
        "stable tie uses original order",
    )

    eq(
        results[1].item_id,
        "second",
        "stable tie second result",
    )


def test_top_k_and_threshold():
    batch = BatchSimilarity()

    candidates = [
        {
            "id": "a",
            "vector": [1.0, 0.0],
        },
        {
            "id": "b",
            "vector": [0.9, 0.1],
        },
        {
            "id": "c",
            "vector": [0.0, 1.0],
        },
    ]

    results = batch.compare(
        [1.0, 0.0],
        candidates,
        top_k=1,
        min_score=0.5,
    )

    eq(
        len(results),
        1,
        "top-k limit",
    )

    eq(
        results[0].item_id,
        "a",
        "top-k best result",
    )


def test_real_chunk_scoring():
    embedder = build_embedder()

    chunks = [
        Chunk(
            chunk_id="software",
            document_id="sire",
            dataset_id="siresoft",
            text=(
                "SireSoft provides professional "
                "software engineering services for clients"
            ),
            chunk_index=0,
            provenance={
                "file": "siresoft.txt",
            },
        ),
        Chunk(
            chunk_id="ai",
            document_id="sire",
            dataset_id="siresoft",
            text=(
                "SireSoft develops artificial intelligence "
                "and machine learning solutions"
            ),
            chunk_index=1,
            provenance={
                "file": "siresoft.txt",
            },
        ),
        Chunk(
            chunk_id="cooking",
            document_id="other",
            dataset_id="test",
            text=(
                "Vegetable recipes and cooking "
                "ideas for the kitchen"
            ),
            chunk_index=0,
        ),
    ]

    scorer = SimilarityScorer(
        embedder
    )

    embedded = scorer.embed_items(
        chunks
    )

    results = scorer.score_query(
        "software engineering services",
        embedded,
        top_k=3,
    )

    eq(
        results[0].item_id,
        "software",
        "real retrieval query ranks software chunk first",
    )

    check(
        results[0].score
        > results[-1].score,
        "relevant chunk score exceeds unrelated chunk",
    )

    eq(
        results[0].item.item.provenance["file"],
        "siresoft.txt",
        "scoring preserves original chunk/provenance",
    )


def test_multilingual_similarity():
    embedder = build_embedder()

    query = embedder.embed_text(
        "اردو software"
    )

    same = embedder.embed_text(
        "اردو software services"
    )

    unrelated = embedder.embed_text(
        "mountains hiking travel"
    )

    metric = CosineSimilarity()

    check(
        metric.score(
            query,
            same,
        )
        > metric.score(
            query,
            unrelated,
        ),
        "multilingual lexical relevance",
    )


def test_embedded_item():
    item = EmbeddedItem(
        item_id="x",
        vector=[1, 2, 3],
        metadata={
            "dataset": "siresoft",
        },
    )

    eq(
        item.vector,
        [1.0, 2.0, 3.0],
        "embedded item numeric normalization",
    )

    eq(
        item.metadata["dataset"],
        "siresoft",
        "embedded item metadata",
    )


def test_validation():
    expect_error(
        ValueError,
        lambda: DotProduct().score(
            [1.0],
            [1.0, 2.0],
        ),
        "dimension mismatch rejected",
    )

    expect_error(
        TypeError,
        lambda: CosineSimilarity().score(
            [1.0, "bad"],
            [1.0, 2.0],
        ),
        "non-numeric vector rejected",
    )

    expect_error(
        ValueError,
        lambda: BatchSimilarity().compare(
            [1.0],
            [[1.0]],
            top_k=0,
        ),
        "invalid top-k rejected",
    )

    expect_error(
        ValueError,
        lambda: EmbeddedItem(
            "",
            [1.0],
        ),
        "empty item id rejected",
    )


def main():
    test_dot_product()
    test_cosine_similarity()
    test_distances()
    test_embedding_result_support()
    test_batch_similarity_ordering()
    test_stable_tie_break()
    test_top_k_and_threshold()
    test_real_chunk_scoring()
    test_multilingual_similarity()
    test_embedded_item()
    test_validation()

    print(
        "SIMILARITY TEST SUITE: PASS"
    )
    print(
        "Assertions passed:",
        ASSERTIONS,
    )
    print(
        "Files validated: 5/5"
    )
    print(
        "Dot/cosine metrics: VALIDATED"
    )
    print(
        "Euclidean/Manhattan distance: VALIDATED"
    )
    print(
        "Batch ranking + stable ties: VALIDATED"
    )
    print(
        "Top-k + threshold filtering: VALIDATED"
    )
    print(
        "Real SireLLM embedding/chunk scoring: VALIDATED"
    )
    print(
        "Multilingual retrieval signal: VALIDATED"
    )
    print(
        "Third-party dependencies: 0"
    )


main()
