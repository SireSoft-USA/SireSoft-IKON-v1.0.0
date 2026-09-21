import os

MATH_BASE = "libs/core/math/"
SERIAL_BASE = "libs/core/serialization/"
PARSER_BASE = "libs/data/parsers/"
TOKENIZER_BASE = "libs/nlp/tokenizer/"
EMBED_BASE = "libs/retrieval/embedding/"
PROTOCOL_BASE = "libs/protocol/"
SERVICE_BASE = "services/embedding_service/"
CONFIG_BASE = "configs/embedding/"

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
        PARSER_BASE,
        [
            "json_parser.py",
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
        ],
    ),
    (
        SERVICE_BASE,
        [
            "artifact.py",
            "state_codec.py",
            "manager.py",
            "service.py",
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
    "embedding.py",
    "config.py",
    "codec.py",
    "validator.py",
    "factory.py",
]:
    path = CONFIG_BASE + filename

    source = open(
        path,
        "r",
        encoding="utf-8",
    ).read()

    if "import " in source:
        raise AssertionError(
            "embedding config implementation contains forbidden import: "
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
ARTIFACT_PATH = (
    "configs/embedding/"
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
        + repr(expected),
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


def cleanup():
    if os.path.isfile(
        ARTIFACT_PATH
    ):
        os.remove(
            ARTIFACT_PATH
        )


def tokenizer(
    variant=1,
):
    encoder = ByteEncoder()
    specials = SpecialTokens()

    if variant == 1:
        corpus = [
            (
                "SireSoft software engineering "
                "application development"
            ),
            (
                "web mobile cloud business systems"
            ),
            (
                "artificial intelligence machine learning"
            ),
            (
                "retrieval augmented generation context"
            ),
            (
                "client software support services"
            ),
        ]
    else:
        corpus = [
            "recipes vegetables kitchen dinner",
            "music travel books paintings",
            "another completely different corpus",
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
            vocab_size=320,
            min_frequency=2,
        )
    )

    return BPETokenizer(
        model,
        encoder,
        specials,
    )


def texts():
    return [
        (
            "SireSoft builds software "
            "engineering systems."
        ),
        (
            "SireSoft provides custom "
            "application development."
        ),
        (
            "Artificial intelligence "
            "supports software automation."
        ),
        (
            "Cooking vegetables in a kitchen."
        ),
    ]


def fit_config():
    return EmbeddingConfig(
        mode="fit",
        model=EmbeddingModelConfig(
            dimension=512,
            min_n=1,
            max_n=2,
            use_idf=True,
            sublinear_tf=True,
            l2_normalize=True,
        ),
        artifact_path=(
            ARTIFACT_PATH
        ),
        persist_after_fit=True,
        metadata={
            "profile": "retrieval",
        },
    )


def dot(
    left,
    right,
):
    total = 0.0

    for index in range(
        len(left)
    ):
        total += (
            left[index]
            * right[index]
        )

    return total


def test_model_config():
    config = (
        EmbeddingModelConfig(
            dimension=256,
            min_n=1,
            max_n=3,
        )
    )

    eq(
        config.dimension,
        256,
        "embedding dimension stored",
    )

    eq(
        config.max_n,
        3,
        "embedding max n-gram stored",
    )

    expect_error(
        ValueError,
        lambda: (
            EmbeddingModelConfig(
                dimension=0
            )
        ),
        "zero dimension rejected",
    )


def test_codec():
    text = (
        '{"mode":"fit",'
        '"model":{'
        '"dimension":384,'
        '"min_n":1,'
        '"max_n":2,'
        '"use_idf":true,'
        '"sublinear_tf":true,'
        '"l2_normalize":true'
        '},'
        '"artifact_path":"embedding.bin",'
        '"persist_after_fit":true,'
        '"metadata":{"profile":"prod"}'
        '}'
    )

    config = (
        EmbeddingConfigCodec()
        .decode_text(
            text
        )
    )

    eq(
        config.mode,
        "fit",
        "codec embedding mode",
    )

    eq(
        config.model.dimension,
        384,
        "codec embedding dimension",
    )

    eq(
        config.persist_after_fit,
        True,
        "codec persist-after-fit setting",
    )


def test_validator():
    config = EmbeddingConfig(
        mode="fit",
        model=EmbeddingModelConfig(
            dimension=32,
            use_idf=False,
        ),
        expected_dimension=32,
    )

    result = (
        EmbeddingConfigValidator()
        .validate(
            config
        )
    )

    codes = [
        item[
            "code"
        ]
        for item
        in result[
            "warnings"
        ]
    ]

    check(
        "LOW_EMBEDDING_DIMENSION"
        in codes,
        "low dimension warning emitted",
    )

    check(
        "FIT_WITH_IDF_DISABLED"
        in codes,
        "fit without IDF warning emitted",
    )

    check(
        "EXPECTED_DIMENSION_UNUSED"
        in codes,
        "unused expected dimension warned",
    )


def test_real_fit():
    result = (
        EmbeddingConfigFactory()
        .initialize(
            fit_config(),
            tokenizer(),
            texts=texts(),
        )
    )

    manager = result[
        "manager"
    ]

    eq(
        manager.info()[
            "dimension"
        ],
        512,
        "configured dimension applied",
    )

    eq(
        manager.info()[
            "idf_fitted"
        ],
        True,
        "configured fit trains IDF",
    )

    eq(
        manager.info()[
            "idf_document_count"
        ],
        4,
        "configured fit uses all runtime texts",
    )

    check(
        os.path.isfile(
            ARTIFACT_PATH
        ),
        "configured embedding artifact persisted",
    )

    check(
        result[
            "artifact"
        ][
            "bytes"
        ] > 0,
        "embedding artifact non-empty",
    )


def test_lexical_signal():
    manager = (
        EmbeddingConfigFactory()
        .initialize(
            fit_config(),
            tokenizer(),
            texts=texts(),
        )[
            "manager"
        ]
    )

    query = manager.embed_text(
        "software engineering"
    )

    related = manager.embed_text(
        (
            "SireSoft builds software "
            "engineering systems."
        )
    )

    unrelated = manager.embed_text(
        (
            "Cooking vegetables "
            "in a kitchen."
        )
    )

    check(
        dot(
            query.vector,
            related.vector,
        )
        >
        dot(
            query.vector,
            unrelated.vector,
        ),
        "configured lexical embedding ranks related text higher",
    )


def test_exact_load_round_trip():
    first = (
        EmbeddingConfigFactory()
        .initialize(
            fit_config(),
            tokenizer(),
            texts=texts(),
        )[
            "manager"
        ]
    )

    load_config = EmbeddingConfig(
        mode="load",
        model=EmbeddingModelConfig(
            dimension=512,
            min_n=1,
            max_n=2,
        ),
        artifact_path=(
            ARTIFACT_PATH
        ),
        expected_dimension=512,
    )

    second = (
        EmbeddingConfigFactory()
        .initialize(
            load_config,
            tokenizer(),
        )[
            "manager"
        ]
    )

    eq(
        second.export_state(),
        first.export_state(),
        "embedding state exact round trip",
    )

    eq(
        second.embed_text(
            "software systems"
        ).vector,
        first.embed_text(
            "software systems"
        ).vector,
        "loaded embedding reproduces exact vector",
    )


def test_tokenizer_signature_boundary():
    EmbeddingConfigFactory().initialize(
        fit_config(),
        tokenizer(
            variant=1
        ),
        texts=texts(),
    )

    expect_error(
        ValueError,
        lambda: (
            EmbeddingConfigFactory()
            .initialize(
                EmbeddingConfig(
                    mode="load",
                    model=(
                        EmbeddingModelConfig(
                            dimension=512
                        )
                    ),
                    artifact_path=(
                        ARTIFACT_PATH
                    ),
                ),
                tokenizer(
                    variant=2
                ),
            )
        ),
        "embedding artifact cannot attach to different tokenizer",
    )


def test_dimension_boundary():
    EmbeddingConfigFactory().initialize(
        fit_config(),
        tokenizer(),
        texts=texts(),
    )

    expect_error(
        ValueError,
        lambda: (
            EmbeddingConfigFactory()
            .initialize(
                EmbeddingConfig(
                    mode="load",
                    model=(
                        EmbeddingModelConfig(
                            dimension=256
                        )
                    ),
                    artifact_path=(
                        ARTIFACT_PATH
                    ),
                    expected_dimension=256,
                ),
                tokenizer(),
            )
        ),
        "embedding artifact expected dimension mismatch rejected",
    )


def test_none_mode():
    result = (
        EmbeddingConfigFactory()
        .initialize(
            EmbeddingConfig(
                mode="none",
                model=(
                    EmbeddingModelConfig(
                        dimension=128,
                    )
                ),
            ),
            tokenizer(),
        )
    )

    eq(
        result[
            "manager"
        ].info()[
            "idf_fitted"
        ],
        False,
        "none mode leaves IDF unfitted",
    )

    eq(
        result[
            "manager"
        ].info()[
            "dimension"
        ],
        128,
        "none mode still applies embedding configuration",
    )


def test_fit_requires_texts():
    expect_error(
        ValueError,
        lambda: (
            EmbeddingConfigFactory()
            .initialize(
                EmbeddingConfig(
                    mode="fit"
                ),
                tokenizer(),
            )
        ),
        "fit mode requires runtime texts",
    )


def test_provider_fit():
    result = (
        EmbeddingConfigFactory()
        .initialize(
            EmbeddingConfig(
                mode="fit",
                model=(
                    EmbeddingModelConfig(
                        dimension=256
                    )
                ),
            ),
            tokenizer(),
            texts_provider=texts,
        )
    )

    eq(
        result[
            "manager"
        ].info()[
            "idf_document_count"
        ],
        4,
        "texts provider feeds embedding fit",
    )


def test_service_creation():
    service = (
        EmbeddingConfigFactory()
        .build_service(
            EmbeddingConfig(
                mode="fit",
                model=(
                    EmbeddingModelConfig(
                        dimension=256
                    )
                ),
            ),
            tokenizer(),
            texts=texts(),
        )
    )

    check(
        isinstance(
            service,
            EmbeddingService,
        ),
        "factory creates EmbeddingService",
    )

    info = service.handle(
        ServiceRequest(
            "emb-info",
            "embedding_service",
            "info",
        )
    )

    eq(
        info.success,
        True,
        "configured embedding service responds",
    )

    eq(
        info.data[
            "info"
        ][
            "idf_fitted"
        ],
        True,
        "configured embedding service starts fitted",
    )

    embedded = service.handle(
        ServiceRequest(
            "emb-text",
            "embedding_service",
            "embed_text",
            payload={
                "text": (
                    "SireSoft software"
                ),
            },
        )
    )

    eq(
        embedded.success,
        True,
        "configured embedding service embeds text",
    )

    eq(
        len(
            embedded.data[
                "embedding"
            ][
                "vector"
            ]
        ),
        256,
        "configured service returns expected vector dimension",
    )


def test_corruption_boundary():
    EmbeddingConfigFactory().initialize(
        fit_config(),
        tokenizer(),
        texts=texts(),
    )

    raw = open(
        ARTIFACT_PATH,
        "rb",
    ).read()

    damaged = bytearray(
        raw
    )

    damaged[
        len(
            damaged
        )
        - 1
    ] ^= 1

    open(
        ARTIFACT_PATH,
        "wb",
    ).write(
        bytes(
            damaged
        )
    )

    expect_error(
        ValueError,
        lambda: (
            EmbeddingConfigFactory()
            .initialize(
                EmbeddingConfig(
                    mode="load",
                    model=(
                        EmbeddingModelConfig(
                            dimension=512
                        )
                    ),
                    artifact_path=(
                        ARTIFACT_PATH
                    ),
                ),
                tokenizer(),
            )
        ),
        "corrupted embedding artifact rejected by checksum",
    )


def main():
    cleanup()

    try:
        test_model_config()
        test_codec()
        test_validator()
        test_real_fit()
        test_lexical_signal()
        test_exact_load_round_trip()
        test_tokenizer_signature_boundary()
        test_dimension_boundary()
        test_none_mode()
        test_fit_requires_texts()
        test_provider_fit()
        test_service_creation()
        test_corruption_boundary()

    finally:
        cleanup()

    print(
        "EMBEDDING CONFIG TEST SUITE: PASS"
    )
    print(
        "Assertions passed:",
        ASSERTIONS,
    )
    print(
        "Files validated: 5/5"
    )
    print(
        "Typed lexical embedding configuration: VALIDATED"
    )
    print(
        "Handwritten JSON decoding: VALIDATED"
    )
    print(
        "Real TF-IDF fitting: VALIDATED"
    )
    print(
        "Lexical retrieval signal: VALIDATED"
    )
    print(
        "Binary artifact persistence/checksum: VALIDATED"
    )
    print(
        "Tokenizer-signature compatibility boundary: VALIDATED"
    )
    print(
        "Exact embedding-state reload: VALIDATED"
    )
    print(
        "EmbeddingService generation: VALIDATED"
    )
    print(
        "Third-party dependencies: 0"
    )


main()
