import os

MATH_BASE = "libs/core/math/"
SERIAL_BASE = "libs/core/serialization/"
TOKENIZER_BASE = "libs/nlp/tokenizer/"
EMBED_BASE = "libs/retrieval/embedding/"
PROTOCOL_BASE = "libs/protocol/"
SERVICE_BASE = "services/embedding_service/"

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
        EMBED_BASE,
        [
            "hash_features.py",
            "idf.py",
            "embedder.py",
        ],
    ),
    (
        PROTOCOL_BASE,
        [
            "error.py",
            "message.py",
            "request.py",
            "response.py",
            "validator.py",
            "codec.py",
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
    "artifact.py",
    "state_codec.py",
    "manager.py",
    "service.py",
]:
    path = SERVICE_BASE + filename

    source = open(
        path,
        "r",
        encoding="utf-8",
    ).read()

    if "import " in source:
        raise AssertionError(
            "embedding_service implementation contains forbidden import: "
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

STATE_PATH = (
    "services/embedding_service/"
    "_test_embedding.slvec"
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
    tolerance=1e-8,
):
    difference = (
        actual
        - expected
    )

    if difference < 0:
        difference = (
            -difference
        )

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


def build_tokenizer(
    variant=1,
):
    byte_encoder = (
        ByteEncoder()
    )

    specials = (
        SpecialTokens()
    )

    if variant == 1:
        corpus = [
            "SireSoft builds software systems.",
            "software engineering services applications",
            "artificial intelligence machine learning",
            "retrieval context company clients projects",
            "اردو software English software",
            "SireSoft software engineering software",
        ]

    else:
        corpus = [
            "completely different tokenizer corpus",
            "cooking recipes vegetables kitchen",
            "music films travel books",
            "different merges different tokens",
        ]

    model = (
        BPETrainer(
            byte_encoder=byte_encoder,
            pair_counter=PairCounter(),
            vocabulary_factory=Vocabulary,
            special_tokens=specials,
        )
        .train(
            corpus,
            vocab_size=320,
            min_frequency=2,
        )
    )

    return BPETokenizer(
        model,
        byte_encoder,
        specials,
    )


def training_texts():
    return [
        "SireSoft builds software systems.",
        "SireSoft provides software engineering services.",
        "machine learning and artificial intelligence",
        "cooking vegetables in a kitchen",
    ]


def dot(
    left,
    right,
):
    total = 0.0
    index = 0

    while index < len(
        left
    ):
        total += (
            left[
                index
            ]
            * right[
                index
            ]
        )

        index += 1

    return total


def norm(
    vector,
):
    total = 0.0

    for value in vector:
        total += (
            value
            * value
        )

    return sqrt(
        total
    )


def fitted_manager(
    dimension=128,
):
    manager = (
        EmbeddingManager(
            tokenizer=build_tokenizer(),
            dimension=dimension,
            min_n=1,
            max_n=2,
        )
    )

    manager.fit(
        training_texts()
    )

    return manager


def test_configuration():
    manager = EmbeddingManager(
        tokenizer=build_tokenizer(),
        dimension=64,
        min_n=1,
        max_n=3,
    )

    info = manager.info()

    eq(
        info[
            "dimension"
        ],
        64,
        "manager dimension",
    )

    eq(
        info[
            "max_n"
        ],
        3,
        "manager max n-gram",
    )

    eq(
        info[
            "idf_fitted"
        ],
        False,
        "new manager IDF not fitted",
    )

    eq(
        len(
            info[
                "tokenizer_signature"
            ]
        ),
        16,
        "tokenizer signature length",
    )

    eq(
        info[
            "representation"
        ],
        "lexical_hashed_tfidf",
        "representation described accurately",
    )


def test_fit_and_vector():
    manager = fitted_manager(
        dimension=128
    )

    info = manager.info()

    eq(
        info[
            "idf_fitted"
        ],
        True,
        "fit marks IDF fitted",
    )

    eq(
        info[
            "idf_document_count"
        ],
        4,
        "fit document count",
    )

    result = manager.embed_text(
        "SireSoft software engineering"
    )

    eq(
        result.dimension(),
        128,
        "embedding dimension",
    )

    check(
        result.token_count > 0,
        "embedding records token count",
    )

    check(
        result.nonzero_features > 0,
        "embedding has features",
    )

    check(
        close(
            norm(
                result.vector
            ),
            1.0,
            tolerance=1e-7,
        ),
        "L2 normalized embedding",
    )


def test_deterministic_embedding():
    manager = fitted_manager()

    first = manager.embed_text(
        "software engineering"
    )

    second = manager.embed_text(
        "software engineering"
    )

    eq(
        first.vector,
        second.vector,
        "same text yields deterministic vector",
    )


def test_lexical_retrieval_signal():
    manager = fitted_manager(
        dimension=2048
    )

    query = manager.embed_text(
        "software engineering"
    )

    related = manager.embed_text(
        "SireSoft provides software engineering services."
    )

    unrelated = manager.embed_text(
        "cooking vegetables in a kitchen"
    )

    related_score = dot(
        query.vector,
        related.vector,
    )

    unrelated_score = dot(
        query.vector,
        unrelated.vector,
    )

    check(
        related_score
        > unrelated_score,
        "lexically related text scores higher",
    )


def test_embed_tokens_matches_text():
    manager = fitted_manager()

    text = (
        "SireSoft builds software"
    )

    token_ids = (
        manager.tokenizer
        .encode(
            text
        )
    )

    by_text = manager.embed_text(
        text
    )

    by_tokens = (
        manager.embed_tokens(
            token_ids
        )
    )

    eq(
        by_text.vector,
        by_tokens.vector,
        "text and token embedding paths agree",
    )


def test_embed_many():
    manager = fitted_manager()

    results = manager.embed_many(
        [
            "software",
            "engineering",
            "SireSoft",
        ]
    )

    eq(
        len(
            results
        ),
        3,
        "embed many count",
    )

    for result in results:
        eq(
            result.dimension(),
            128,
            "embed many dimension",
        )


def test_state_round_trip():
    tokenizer = build_tokenizer()

    source = EmbeddingManager(
        tokenizer=tokenizer,
        dimension=96,
        min_n=1,
        max_n=2,
    )

    source.fit(
        training_texts()
    )

    state = source.export_state()

    restored = EmbeddingManager(
        tokenizer=tokenizer,
        dimension=32,
    )

    restored.load_state(
        state,
        expected_dimension=96,
    )

    eq(
        restored.export_state(),
        state,
        "embedding state exact round trip",
    )

    eq(
        restored.embed_text(
            "software systems"
        ).vector,
        source.embed_text(
            "software systems"
        ).vector,
        "restored embedding state preserves vectors",
    )


def test_dimension_validation():
    source = fitted_manager(
        dimension=96
    )

    target = EmbeddingManager(
        tokenizer=source.tokenizer,
        dimension=32,
    )

    expect_error(
        ValueError,
        lambda: target.load_state(
            source.export_state(),
            expected_dimension=128,
        ),
        "expected embedding dimension mismatch rejected",
    )


def test_tokenizer_signature_validation():
    source = EmbeddingManager(
        tokenizer=build_tokenizer(
            variant=1
        ),
        dimension=64,
    )

    source.fit(
        training_texts()
    )

    target = EmbeddingManager(
        tokenizer=build_tokenizer(
            variant=2
        ),
        dimension=64,
    )

    expect_error(
        ValueError,
        lambda: target.load_state(
            source.export_state()
        ),
        "state from different tokenizer rejected",
    )


def test_protocol_safe_state():
    manager = fitted_manager(
        dimension=64
    )

    state = manager.export_state()

    codec = ProtocolCodec()

    request = ServiceRequest(
        "state",
        "embedding_service",
        "load_state",
        payload={
            "state": state,
            "expected_dimension": 64,
        },
    )

    restored = (
        codec.decode_request(
            codec.encode_request(
                request
            )
        )
    )

    eq(
        restored.payload[
            "state"
        ],
        state,
        "embedding state survives protocol codec",
    )


def test_binary_state_file():
    if os.path.exists(
        STATE_PATH
    ):
        os.remove(
            STATE_PATH
        )

    tokenizer = build_tokenizer()

    source = EmbeddingManager(
        tokenizer=tokenizer,
        dimension=80,
    )

    source.fit(
        training_texts()
    )

    saved = source.save_state_file(
        STATE_PATH
    )

    check(
        saved[
            "bytes"
        ] > 0,
        "embedding state artifact written",
    )

    target = EmbeddingManager(
        tokenizer=tokenizer,
        dimension=16,
    )

    target.load_state_file(
        STATE_PATH,
        expected_dimension=80,
    )

    eq(
        target.export_state(),
        source.export_state(),
        "binary embedding state exact round trip",
    )


def test_state_corruption_detection():
    manager = fitted_manager(
        dimension=64
    )

    artifact = EmbeddingArtifact.from_dict(
        manager.export_state()
    )

    encoded = bytearray(
        manager.state_codec.encode(
            artifact
        )
    )

    encoded[
        -1
    ] ^= 0x01

    expect_error(
        ValueError,
        lambda: manager.state_codec.decode(
            bytes(
                encoded
            )
        ),
        "embedding state checksum detects corruption",
    )


def test_service_flow():
    manager = EmbeddingManager(
        tokenizer=build_tokenizer(),
        dimension=64,
    )

    service = EmbeddingService(
        manager
    )

    fitted = service.handle(
        ServiceRequest(
            "s1",
            "embedding_service",
            "fit",
            payload={
                "texts": training_texts(),
            },
        )
    )

    eq(
        fitted.success,
        True,
        "service fit succeeds",
    )

    embedded = service.handle(
        ServiceRequest(
            "s2",
            "embedding_service",
            "embed_text",
            payload={
                "text": "software engineering",
            },
        )
    )

    eq(
        embedded.success,
        True,
        "service embed text succeeds",
    )

    eq(
        len(
            embedded.data[
                "embedding"
            ][
                "vector"
            ]
        ),
        64,
        "service vector dimension",
    )

    many = service.handle(
        ServiceRequest(
            "s3",
            "embedding_service",
            "embed_many",
            payload={
                "texts": [
                    "software",
                    "engineering",
                ],
            },
        )
    )

    eq(
        many.data[
            "count"
        ],
        2,
        "service embed many count",
    )


def test_service_state_transfer():
    tokenizer = build_tokenizer()

    source_service = EmbeddingService(
        EmbeddingManager(
            tokenizer=tokenizer,
            dimension=72,
        )
    )

    source_service.handle(
        ServiceRequest(
            "f",
            "embedding_service",
            "fit",
            payload={
                "texts": training_texts(),
            },
        )
    )

    exported = source_service.handle(
        ServiceRequest(
            "e",
            "embedding_service",
            "export_state",
        )
    )

    target_service = EmbeddingService(
        EmbeddingManager(
            tokenizer=tokenizer,
            dimension=16,
        )
    )

    loaded = target_service.handle(
        ServiceRequest(
            "l",
            "embedding_service",
            "load_state",
            payload={
                "state": exported.data[
                    "state"
                ],
                "expected_dimension": 72,
            },
        )
    )

    eq(
        loaded.success,
        True,
        "service state transfer succeeds",
    )

    first = source_service.handle(
        ServiceRequest(
            "a",
            "embedding_service",
            "embed_text",
            payload={
                "text": "SireSoft software",
            },
        )
    )

    second = target_service.handle(
        ServiceRequest(
            "b",
            "embedding_service",
            "embed_text",
            payload={
                "text": "SireSoft software",
            },
        )
    )

    eq(
        first.data[
            "embedding"
        ][
            "vector"
        ],
        second.data[
            "embedding"
        ][
            "vector"
        ],
        "service transfer preserves embeddings",
    )


def test_service_protocol_round_trip():
    service = EmbeddingService(
        EmbeddingManager(
            tokenizer=build_tokenizer(),
            dimension=48,
        )
    )

    codec = ProtocolCodec()

    fit_request = ServiceRequest(
        "protocol-fit",
        "embedding_service",
        "fit",
        payload={
            "texts": training_texts(),
        },
        trace_id="trace-embedding",
    )

    fit_request = (
        codec.decode_request(
            codec.encode_request(
                fit_request
            )
        )
    )

    fit_response = (
        service.handle(
            fit_request
        )
    )

    fit_response = (
        codec.decode_response(
            codec.encode_response(
                fit_response
            )
        )
    )

    eq(
        fit_response.success,
        True,
        "embedding fit survives protocol codec",
    )

    eq(
        fit_response.trace_id,
        "trace-embedding",
        "embedding trace preserved",
    )

    embed_request = ServiceRequest(
        "protocol-embed",
        "embedding_service",
        "embed_text",
        payload={
            "text": "SireSoft software engineering",
        },
    )

    embed_request = (
        codec.decode_request(
            codec.encode_request(
                embed_request
            )
        )
    )

    embed_response = service.handle(
        embed_request
    )

    embed_response = (
        codec.decode_response(
            codec.encode_response(
                embed_response
            )
        )
    )

    eq(
        len(
            embed_response.data[
                "embedding"
            ][
                "vector"
            ]
        ),
        48,
        "embedding vector survives binary protocol",
    )


def test_service_configure():
    service = EmbeddingService(
        EmbeddingManager(
            tokenizer=build_tokenizer(),
            dimension=32,
        )
    )

    response = service.handle(
        ServiceRequest(
            "cfg",
            "embedding_service",
            "configure",
            payload={
                "dimension": 40,
                "min_n": 2,
                "max_n": 3,
                "use_idf": False,
                "l2_normalize": True,
            },
        )
    )

    eq(
        response.success,
        True,
        "service configure succeeds",
    )

    eq(
        response.data[
            "info"
        ][
            "dimension"
        ],
        40,
        "service reconfigures dimension",
    )

    eq(
        response.data[
            "info"
        ][
            "use_idf"
        ],
        False,
        "service configures IDF mode",
    )


def test_errors():
    service = EmbeddingService(
        EmbeddingManager(
            tokenizer=build_tokenizer(),
        )
    )

    wrong = service.handle(
        ServiceRequest(
            "w",
            "rag_service",
            "info",
        )
    )

    eq(
        wrong.error.code,
        "INVALID_REQUEST",
        "wrong target service rejected",
    )

    missing = service.handle(
        ServiceRequest(
            "m",
            "embedding_service",
            "embed_text",
            payload={},
        )
    )

    eq(
        missing.error.code,
        "INVALID_REQUEST",
        "missing embedding text rejected",
    )

    invalid = service.handle(
        ServiceRequest(
            "c",
            "embedding_service",
            "configure",
            payload={
                "dimension": 0,
            },
        )
    )

    eq(
        invalid.error.code,
        "INVALID_REQUEST",
        "invalid dimension rejected",
    )


def test_validation():
    expect_error(
        TypeError,
        lambda: EmbeddingManager(
            tokenizer=None
        ),
        "missing tokenizer rejected",
    )

    manager = EmbeddingManager(
        tokenizer=build_tokenizer()
    )

    expect_error(
        ValueError,
        lambda: manager.fit(
            []
        ),
        "empty fit corpus rejected",
    )

    expect_error(
        TypeError,
        lambda: EmbeddingService(
            manager
        ).handle(
            {}
        ),
        "non-ServiceRequest rejected",
    )


def main():
    try:
        test_configuration()
        test_fit_and_vector()
        test_deterministic_embedding()
        test_lexical_retrieval_signal()
        test_embed_tokens_matches_text()
        test_embed_many()
        test_state_round_trip()
        test_dimension_validation()
        test_tokenizer_signature_validation()
        test_protocol_safe_state()
        test_binary_state_file()
        test_state_corruption_detection()
        test_service_flow()
        test_service_state_transfer()
        test_service_protocol_round_trip()
        test_service_configure()
        test_errors()
        test_validation()

    finally:
        if os.path.exists(
            STATE_PATH
        ):
            os.remove(
                STATE_PATH
            )

    print(
        "EMBEDDING SERVICE TEST SUITE: PASS"
    )
    print(
        "Assertions passed:",
        ASSERTIONS,
    )
    print(
        "Files validated: 4/4"
    )
    print(
        "Tokenizer-backed hashed TF-IDF fitting: VALIDATED"
    )
    print(
        "Deterministic lexical embeddings: VALIDATED"
    )
    print(
        "L2 normalization/dimensional integrity: VALIDATED"
    )
    print(
        "Tokenizer signature compatibility: VALIDATED"
    )
    print(
        "State export/load + binary checksum: VALIDATED"
    )
    print(
        "Protocol-safe embedding vectors/state: VALIDATED"
    )
    print(
        "Service configure/fit/embed operations: VALIDATED"
    )
    print(
        "Third-party dependencies: 0"
    )


main()
