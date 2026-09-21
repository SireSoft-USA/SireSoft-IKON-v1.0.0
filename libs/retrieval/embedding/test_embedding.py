MATH_BASE = "libs/core/math/"
TOKENIZER_BASE = "libs/nlp/tokenizer/"
CHUNK_BASE = "libs/retrieval/chunking/"
EMBED_BASE = "libs/retrieval/embedding/"

namespace = {
    "__builtins__": __builtins__,
}

path = MATH_BASE + "scalar.py"
source = open(path, "r", encoding="utf-8").read()
exec(compile(source, path, "exec"), namespace)

for filename in [
    "special_tokens.py",
    "byte_encoder.py",
    "pair_counter.py",
    "vocabulary.py",
    "bpe_trainer.py",
    "bpe_tokenizer.py",
]:
    path = TOKENIZER_BASE + filename
    source = open(path, "r", encoding="utf-8").read()
    exec(compile(source, path, "exec"), namespace)

path = CHUNK_BASE + "chunk.py"
source = open(path, "r", encoding="utf-8").read()
exec(compile(source, path, "exec"), namespace)

for filename in [
    "hash_features.py",
    "idf.py",
    "embedder.py",
]:
    path = EMBED_BASE + filename
    source = open(path, "r", encoding="utf-8").read()

    if "import " in source:
        raise AssertionError(
            "embedding implementation contains forbidden import: "
            + filename
        )

    exec(compile(source, path, "exec"), namespace)

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


def close(actual, expected, tolerance=1e-8):
    difference = actual - expected

    if difference < 0:
        difference = -difference

    return difference <= tolerance


def expect_error(error_type, fn, message):
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
            "SireSoft builds software systems and web applications.",
            "software engineering and application development",
            "machine learning artificial intelligence retrieval",
            "company services clients projects engineering",
            "اردو text English text software",
            "SireSoft SireSoft software software",
        ],
        vocab_size=320,
        min_frequency=2,
    )

    return BPETokenizer(
        model,
        byte_encoder,
        specials,
    )


def dot(left, right):
    total = 0.0
    index = 0

    while index < len(left):
        total += left[index] * right[index]
        index += 1

    return total


def norm(vector):
    total = 0.0

    for value in vector:
        total += value * value

    return sqrt(total)


def test_hashed_features_deterministic():
    extractor = HashedNGramFeatures(
        dimension=64,
        min_n=1,
        max_n=2,
    )

    tokens = [1, 2, 3, 2, 3]

    first = extractor.extract(tokens)
    second = extractor.extract(tokens)

    eq(
        first,
        second,
        "hashed features deterministic",
    )

    check(
        len(first) > 0,
        "hashed features non-empty",
    )

    for bucket in first:
        check(
            0 <= bucket < 64,
            "hashed bucket in range",
        )


def test_ngram_information():
    extractor = HashedNGramFeatures(
        dimension=4096,
        min_n=2,
        max_n=2,
        use_sign_hash=False,
    )

    first = extractor.extract(
        [1, 2, 3]
    )

    second = extractor.extract(
        [1, 3, 2]
    )

    check(
        first != second,
        "bigrams preserve token order information",
    )


def test_idf_fit():
    model = IDFModel(
        dimension=8
    )

    model.fit_feature_sets(
        [
            {1: True, 2: True},
            {1: True, 3: True},
            {1: True, 4: True},
        ]
    )

    eq(
        model.document_count,
        3,
        "IDF document count",
    )

    eq(
        model.document_frequency[1],
        3,
        "common feature df",
    )

    eq(
        model.document_frequency[2],
        1,
        "rare feature df",
    )

    check(
        model.weight(2) > model.weight(1),
        "rare feature receives larger IDF",
    )


def test_embedding_dimension_and_norm():
    tokenizer = build_tokenizer()

    embedder = HashingTFIDFEmbedder(
        tokenizer,
        dimension=128,
    )

    embedder.fit(
        [
            "software engineering",
            "machine learning",
            "company services",
        ]
    )

    result = embedder.embed_text(
        "software engineering"
    )

    eq(
        result.dimension(),
        128,
        "embedding dimension",
    )

    check(
        close(
            norm(result.vector),
            1.0,
            tolerance=1e-7,
        ),
        "embedding L2 normalized",
    )

    check(
        result.nonzero_features > 0,
        "embedding contains active features",
    )


def test_same_text_same_embedding():
    tokenizer = build_tokenizer()

    embedder = HashingTFIDFEmbedder(
        tokenizer,
        dimension=128,
    )

    embedder.fit(
        [
            "SireSoft software engineering",
            "machine learning AI",
            "web applications",
        ]
    )

    first = embedder.embed_text(
        "SireSoft software engineering"
    ).vector

    second = embedder.embed_text(
        "SireSoft software engineering"
    ).vector

    eq(
        first,
        second,
        "same text produces identical embedding",
    )

    check(
        close(
            dot(first, second),
            1.0,
            tolerance=1e-7,
        ),
        "self cosine similarity equals one",
    )


def test_lexical_relevance_signal():
    tokenizer = build_tokenizer()

    embedder = HashingTFIDFEmbedder(
        tokenizer,
        dimension=1024,
        min_n=1,
        max_n=2,
    )

    corpus = [
        "SireSoft develops software applications for clients",
        "professional software engineering services",
        "machine learning artificial intelligence systems",
        "cooking recipes vegetables kitchen dinner",
        "mountains rivers travel hiking adventure",
    ]

    embedder.fit(corpus)

    query = embedder.embed_text(
        "software engineering services"
    ).vector

    related = embedder.embed_text(
        "professional software engineering services"
    ).vector

    unrelated = embedder.embed_text(
        "cooking vegetables in the kitchen"
    ).vector

    check(
        dot(query, related)
        > dot(query, unrelated),
        "lexically related document scores above unrelated text",
    )


def test_idf_changes_weighting():
    tokenizer = build_tokenizer()

    no_idf = HashingTFIDFEmbedder(
        tokenizer,
        dimension=512,
        use_idf=False,
    )

    with_idf = HashingTFIDFEmbedder(
        tokenizer,
        dimension=512,
        use_idf=True,
    )

    corpus = [
        "software common alpha",
        "software common beta",
        "software common rareword",
    ]

    with_idf.fit(corpus)

    plain = no_idf.embed_text(
        "software rareword"
    ).vector

    weighted = with_idf.embed_text(
        "software rareword"
    ).vector

    check(
        plain != weighted,
        "fitted IDF changes embedding weights",
    )


def test_real_chunk_embedding():
    tokenizer = build_tokenizer()

    embedder = HashingTFIDFEmbedder(
        tokenizer,
        dimension=128,
    )

    chunks = [
        Chunk(
            chunk_id="c1",
            document_id="sire",
            dataset_id="siresoft",
            text="SireSoft software engineering services",
            chunk_index=0,
            provenance={"file": "siresoft.txt"},
        ),
        Chunk(
            chunk_id="c2",
            document_id="sire",
            dataset_id="siresoft",
            text="SireSoft AI and machine learning services",
            chunk_index=1,
            provenance={"file": "siresoft.txt"},
        ),
    ]

    embedder.fit_chunks(chunks)

    first = embedder.embed_chunk(
        chunks[0]
    )

    second = embedder.embed_chunk(
        chunks[1]
    )

    eq(
        first.dimension(),
        128,
        "chunk embedding dimension",
    )

    eq(
        second.dimension(),
        128,
        "second chunk embedding dimension",
    )

    eq(
        chunks[0].provenance["file"],
        "siresoft.txt",
        "embedding does not mutate chunk provenance",
    )


def test_multilingual_embedding():
    tokenizer = build_tokenizer()

    embedder = HashingTFIDFEmbedder(
        tokenizer,
        dimension=256,
    )

    texts = [
        "اردو زبان software",
        "中文 software",
        "English software",
    ]

    embedder.fit(texts)

    for text in texts:
        result = embedder.embed_text(
            text
        )

        check(
            result.token_count > 0,
            "multilingual token count",
        )

        check(
            result.nonzero_features > 0,
            "multilingual embedding non-empty",
        )

        check(
            close(
                norm(result.vector),
                1.0,
                tolerance=1e-7,
            ),
            "multilingual vector normalized",
        )


def test_empty_text():
    tokenizer = build_tokenizer()

    result = HashingTFIDFEmbedder(
        tokenizer,
        dimension=64,
    ).embed_text(
        ""
    )

    eq(
        result.token_count,
        0,
        "empty text token count",
    )

    eq(
        result.nonzero_features,
        0,
        "empty embedding has no features",
    )

    check(
        close(
            norm(result.vector),
            0.0,
        ),
        "empty embedding is zero vector",
    )


def test_state_round_trip():
    tokenizer = build_tokenizer()

    original = HashingTFIDFEmbedder(
        tokenizer,
        dimension=128,
        min_n=1,
        max_n=2,
    )

    original.fit(
        [
            "software engineering",
            "AI engineering",
            "company information",
        ]
    )

    restored = HashingTFIDFEmbedder(
        tokenizer,
        dimension=128,
        min_n=1,
        max_n=2,
    )

    restored.load_state_dict(
        original.state_dict()
    )

    text = "software AI engineering"

    eq(
        original.embed_text(text).vector,
        restored.embed_text(text).vector,
        "embedder state restores exactly",
    )


def test_validation():
    tokenizer = build_tokenizer()

    expect_error(
        ValueError,
        lambda: HashedNGramFeatures(
            dimension=0,
        ),
        "invalid embedding dimension",
    )

    expect_error(
        ValueError,
        lambda: HashedNGramFeatures(
            min_n=2,
            max_n=1,
        ),
        "invalid ngram range",
    )

    expect_error(
        ValueError,
        lambda: IDFModel(
            8
        ).fit_feature_sets(
            []
        ),
        "empty IDF corpus rejected",
    )

    expect_error(
        TypeError,
        lambda: HashingTFIDFEmbedder(
            tokenizer
        ).embed_text(
            123
        ),
        "non-text embedding rejected",
    )


def main():
    test_hashed_features_deterministic()
    test_ngram_information()
    test_idf_fit()
    test_embedding_dimension_and_norm()
    test_same_text_same_embedding()
    test_lexical_relevance_signal()
    test_idf_changes_weighting()
    test_real_chunk_embedding()
    test_multilingual_embedding()
    test_empty_text()
    test_state_round_trip()
    test_validation()

    print("EMBEDDING TEST SUITE: PASS")
    print("Assertions passed:", ASSERTIONS)
    print("Files validated: 3/3")
    print("Deterministic hashed n-grams: VALIDATED")
    print("TF-IDF fitting/state: VALIDATED")
    print("L2-normalized dense vectors: VALIDATED")
    print("Lexical relevance signal: VALIDATED")
    print("Real SireLLM chunk/tokenizer integration: VALIDATED")
    print("Multilingual byte-BPE embedding: VALIDATED")
    print("Third-party dependencies: 0")


main()
