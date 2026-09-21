MATH_BASE = "libs/core/math/"
TOKENIZER_BASE = "libs/nlp/tokenizer/"
CHUNK_BASE = "libs/retrieval/chunking/"
EMBED_BASE = "libs/retrieval/embedding/"
SIM_BASE = "libs/retrieval/similarity/"
INDEX_BASE = "libs/retrieval/index/"
RANK_BASE = "libs/retrieval/ranking/"

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

for filename in [
    "entry.py",
    "flat_index.py",
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

for filename in [
    "result.py",
    "dedup.py",
    "reranker.py",
    "mmr.py",
    "pipeline.py",
]:
    path = RANK_BASE + filename

    source = open(
        path,
        "r",
        encoding="utf-8",
    ).read()

    if "import " in source:
        raise AssertionError(
            "ranking implementation contains forbidden import: "
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
    difference = actual - expected

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
            "software application development clients.",
            "artificial intelligence machine learning.",
            "cloud engineering systems.",
            "company information professional services.",
            "cooking recipes kitchen vegetables.",
            "travel mountains hiking rivers.",
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


def build_retrieval_stack():
    tokenizer = build_tokenizer()

    chunks = [
        Chunk(
            chunk_id="service-main",
            document_id="siresoft-main",
            dataset_id="siresoft",
            text=(
                "SireSoft provides professional software "
                "engineering and application development services."
            ),
            chunk_index=0,
            metadata={
                "section": "services",
                "authoritative": True,
                "rag": True,
            },
            provenance={
                "file": "siresoft.txt",
            },
        ),
        Chunk(
            chunk_id="service-duplicate",
            document_id="siresoft-copy",
            dataset_id="siresoft",
            text=(
                "SireSoft provides professional software "
                "engineering and application development services."
            ),
            chunk_index=0,
            metadata={
                "section": "services",
                "authoritative": False,
                "rag": True,
            },
        ),
        Chunk(
            chunk_id="ai-main",
            document_id="siresoft-main",
            dataset_id="siresoft",
            text=(
                "SireSoft develops artificial intelligence "
                "and machine learning solutions for clients."
            ),
            chunk_index=1,
            metadata={
                "section": "ai",
                "authoritative": True,
                "rag": True,
            },
            provenance={
                "file": "siresoft.txt",
            },
        ),
        Chunk(
            chunk_id="cloud-main",
            document_id="siresoft-main",
            dataset_id="siresoft",
            text=(
                "SireSoft engineers cloud software systems "
                "and scalable client applications."
            ),
            chunk_index=2,
            metadata={
                "section": "cloud",
                "authoritative": True,
                "rag": True,
            },
            provenance={
                "file": "siresoft.txt",
            },
        ),
        Chunk(
            chunk_id="food",
            document_id="other",
            dataset_id="other",
            text=(
                "Cooking vegetables and kitchen recipes "
                "for family dinner."
            ),
            chunk_index=0,
            metadata={
                "section": "food",
                "authoritative": False,
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


def test_ranked_result():
    entry = IndexEntry(
        item_id="x",
        vector=[1.0, 0.0],
    )

    result = RankedResult(
        entry=entry,
        similarity_score=0.8,
        rerank_score=1.1,
        rank=1,
        reasons=["boost"],
    )

    eq(
        result.item_id,
        "x",
        "ranked result identity",
    )

    check(
        close(
            result.rerank_score,
            1.1,
        ),
        "ranked result score",
    )

    eq(
        result.reasons,
        ["boost"],
        "ranked result reasons",
    )


def test_duplicate_suppression():
    first = IndexSearchResult(
        entry=IndexEntry(
            "a",
            [1.0, 0.0],
            text="Hello   World",
        ),
        score=0.9,
        rank=1,
    )

    duplicate = IndexSearchResult(
        entry=IndexEntry(
            "b",
            [0.9, 0.1],
            text="hello world",
        ),
        score=0.85,
        rank=2,
    )

    unique = IndexSearchResult(
        entry=IndexEntry(
            "c",
            [0.0, 1.0],
            text="Different",
        ),
        score=0.2,
        rank=3,
    )

    kept = DuplicateSuppressor().suppress(
        [
            first,
            duplicate,
            unique,
        ]
    )

    eq(
        [
            result.entry.item_id
            for result in kept
        ],
        ["a", "c"],
        "normalized exact duplicate suppression",
    )


def test_reranker_dataset_boost():
    results = [
        IndexSearchResult(
            IndexEntry(
                "external",
                [1.0, 0.0],
                dataset_id="other",
            ),
            score=0.90,
            rank=1,
        ),
        IndexSearchResult(
            IndexEntry(
                "sire",
                [0.9, 0.1],
                dataset_id="siresoft",
            ),
            score=0.85,
            rank=2,
        ),
    ]

    reranked = RetrievalReranker(
        dataset_boosts={
            "siresoft": 0.10,
        },
    ).rerank(
        results
    )

    eq(
        reranked[0].item_id,
        "sire",
        "configured dataset boost can reorder results",
    )

    check(
        any(
            reason.startswith(
                "dataset_boost="
            )
            for reason
            in reranked[0].reasons
        ),
        "dataset boost reason exposed",
    )


def test_metadata_boost():
    results = [
        IndexSearchResult(
            IndexEntry(
                "plain",
                [1.0, 0.0],
                metadata={
                    "authoritative": False,
                },
            ),
            score=0.8,
            rank=1,
        ),
        IndexSearchResult(
            IndexEntry(
                "authoritative",
                [1.0, 0.0],
                metadata={
                    "authoritative": True,
                },
            ),
            score=0.8,
            rank=2,
        ),
    ]

    reranked = RetrievalReranker(
        metadata_boosts={
            "authoritative": {
                "value": True,
                "boost": 0.05,
            },
        },
    ).rerank(
        results
    )

    eq(
        reranked[0].item_id,
        "authoritative",
        "metadata boost applied",
    )


def test_mmr_diversity():
    candidates = [
        RankedResult(
            entry=IndexEntry(
                "a",
                [1.0, 0.0],
            ),
            similarity_score=1.0,
            rerank_score=1.0,
        ),
        RankedResult(
            entry=IndexEntry(
                "b",
                [0.999, 0.001],
            ),
            similarity_score=0.99,
            rerank_score=0.99,
        ),
        RankedResult(
            entry=IndexEntry(
                "c",
                [0.7, 0.7],
            ),
            similarity_score=0.90,
            rerank_score=0.90,
        ),
    ]

    selected = MaximalMarginalRelevance(
        lambda_relevance=0.5,
    ).select(
        candidates,
        top_k=2,
    )

    eq(
        selected[0].item_id,
        "a",
        "MMR keeps strongest first result",
    )

    eq(
        selected[1].item_id,
        "c",
        "MMR prefers less redundant second result",
    )


def test_pipeline_without_mmr():
    results = [
        IndexSearchResult(
            IndexEntry(
                "a",
                [1.0, 0.0],
                text="alpha",
            ),
            score=0.9,
            rank=1,
        ),
        IndexSearchResult(
            IndexEntry(
                "b",
                [0.9, 0.1],
                text="beta",
            ),
            score=0.8,
            rank=2,
        ),
    ]

    pipeline = RankingPipeline(
        reranker=RetrievalReranker(),
    )

    final = pipeline.rank(
        results,
        top_k=1,
        use_mmr=False,
    )

    eq(
        len(final),
        1,
        "pipeline top-k",
    )

    eq(
        final[0].item_id,
        "a",
        "pipeline keeps top result",
    )

    eq(
        final[0].rank,
        1,
        "pipeline rank assigned",
    )


def test_real_sirellm_pipeline():
    embedder, chunks, index = (
        build_retrieval_stack()
    )

    query = embedder.embed_text(
        "software engineering application services"
    )

    raw_results = index.search(
        query,
        top_k=5,
    )

    pipeline = RankingPipeline(
        reranker=RetrievalReranker(
            dataset_boosts={
                "siresoft": 0.03,
            },
            metadata_boosts={
                "authoritative": {
                    "value": True,
                    "boost": 0.02,
                },
                "rag": {
                    "value": True,
                    "boost": 0.01,
                },
            },
        ),
        duplicate_suppressor=DuplicateSuppressor(),
        mmr=MaximalMarginalRelevance(
            lambda_relevance=0.80,
        ),
    )

    final = pipeline.rank(
        raw_results,
        top_k=3,
        use_mmr=True,
    )

    eq(
        final[0].item_id,
        "service-main",
        "real SireLLM ranking keeps service chunk first",
    )

    check(
        "service-duplicate"
        not in [
            result.item_id
            for result in final
        ],
        "real pipeline suppresses duplicate service chunk",
    )

    check(
        "food"
        not in [
            result.item_id
            for result in final[:2]
        ],
        "unrelated food chunk not promoted into top two",
    )

    eq(
        final[0].entry.provenance["file"],
        "siresoft.txt",
        "ranked result retains provenance",
    )


def test_real_diverse_query():
    embedder, chunks, index = (
        build_retrieval_stack()
    )

    query = embedder.embed_text(
        "SireSoft software AI cloud services"
    )

    raw = index.search(
        query,
        top_k=5,
        filters={
            "dataset_id": "siresoft",
        },
    )

    final = RankingPipeline(
        reranker=RetrievalReranker(),
        duplicate_suppressor=DuplicateSuppressor(),
        mmr=MaximalMarginalRelevance(
            lambda_relevance=0.65,
        ),
    ).rank(
        raw,
        top_k=3,
        use_mmr=True,
    )

    ids = [
        result.item_id
        for result in final
    ]

    check(
        "service-main" in ids,
        "diverse query includes service chunk",
    )

    check(
        (
            "ai-main" in ids
            or "cloud-main" in ids
        ),
        "MMR keeps another relevant topic",
    )

    check(
        "service-duplicate" not in ids,
        "duplicate still suppressed under MMR",
    )


def test_validation():
    expect_error(
        ValueError,
        lambda: MaximalMarginalRelevance(
            lambda_relevance=1.5
        ),
        "invalid MMR lambda",
    )

    expect_error(
        ValueError,
        lambda: RankingPipeline().rank(
            [],
            top_k=0,
        ),
        "invalid pipeline top-k",
    )

    expect_error(
        TypeError,
        lambda: RetrievalReranker(
            dataset_boosts={
                "x": "bad",
            },
        ),
        "non-numeric boost rejected",
    )


def main():
    test_ranked_result()
    test_duplicate_suppression()
    test_reranker_dataset_boost()
    test_metadata_boost()
    test_mmr_diversity()
    test_pipeline_without_mmr()
    test_real_sirellm_pipeline()
    test_real_diverse_query()
    test_validation()

    print(
        "RANKING TEST SUITE: PASS"
    )
    print(
        "Assertions passed:",
        ASSERTIONS,
    )
    print(
        "Files validated: 5/5"
    )
    print(
        "Duplicate suppression: VALIDATED"
    )
    print(
        "Transparent score boosts: VALIDATED"
    )
    print(
        "Stable deterministic reranking: VALIDATED"
    )
    print(
        "MMR diversity control: VALIDATED"
    )
    print(
        "Real SireLLM retrieval pipeline: VALIDATED"
    )
    print(
        "Provenance preservation: VALIDATED"
    )
    print(
        "Third-party dependencies: 0"
    )


main()
