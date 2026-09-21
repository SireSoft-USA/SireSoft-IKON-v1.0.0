MATH_BASE = "libs/core/math/"
SERIAL_BASE = "libs/core/serialization/"
PARSERS_BASE = "libs/data/parsers/"
TOKENIZER_BASE = "libs/nlp/tokenizer/"
CORPUS_BASE = "libs/nlp/corpus/"
CHUNK_BASE = "libs/retrieval/chunking/"
EMBED_BASE = "libs/retrieval/embedding/"
SIM_BASE = "libs/retrieval/similarity/"
INDEX_BASE = "libs/retrieval/index/"
RANK_BASE = "libs/retrieval/ranking/"
PROTOCOL_BASE = "libs/protocol/"
SERVICE_BASE = "services/retrieval_service/"
CONFIG_BASE = "configs/retrieval/"

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
        PARSERS_BASE,
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
    (
        SERVICE_BASE,
        [
            "document_store.py",
            "result.py",
            "persistence.py",
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
    "chunking.py",
    "search.py",
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
            "retrieval config implementation contains forbidden import: "
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


def build_tokenizer():
    encoder = ByteEncoder()
    specials = SpecialTokens()

    corpus = [
        "SireSoft software engineering development services",
        "custom applications web mobile cloud systems",
        "machine learning artificial intelligence software",
        "cooking recipes vegetables kitchen dinner",
        "client projects professional support engineering",
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


def documents():
    return [
        {
            "document_id": "sire-company",
            "dataset_id": "siresoft",
            "text": (
                "SireSoft provides professional software engineering "
                "and custom application development services for clients. "
                "The company builds web, mobile, and cloud business systems."
            ),
            "metadata": {
                "kind": "company",
                "priority": "primary",
            },
            "provenance": {
                "source_file": (
                    "datasets/raw/siresoft/siresoft.txt"
                ),
            },
        },
        {
            "document_id": "food",
            "dataset_id": "general",
            "text": (
                "A cooking recipe uses vegetables, a kitchen, "
                "spices, and dinner ingredients."
            ),
            "metadata": {
                "kind": "food",
            },
        },
        {
            "document_id": "ai",
            "dataset_id": "general",
            "text": (
                "Machine learning and artificial intelligence "
                "are used in software systems and automation."
            ),
            "metadata": {
                "kind": "technology",
            },
        },
    ]


def sample_config():
    return RetrievalConfig(
        embedding=(
            RetrievalEmbeddingConfig(
                dimension=512,
                min_n=1,
                max_n=2,
                use_idf=True,
            )
        ),
        chunking=(
            RetrievalChunkingConfig(
                max_chars=1000,
                overlap_chars=0,
                min_chunk_chars=0,
            )
        ),
        search=(
            RetrievalSearchConfig(
                top_k=2,
                search_k=3,
                use_mmr=True,
                mmr_lambda=0.8,
                similarity_weight=1.0,
                dataset_boosts={
                    "siresoft": 0.1,
                },
                metadata_boosts={
                    "priority": {
                        "value": "primary",
                        "boost": 0.05,
                    },
                },
            )
        ),
        default_index_mode="replace",
        default_refit=True,
        metadata={
            "profile": "sire-rag",
        },
    )


def test_embedding_config():
    config = (
        RetrievalEmbeddingConfig(
            dimension=256,
            min_n=1,
            max_n=3,
        )
    )

    eq(
        config.max_n,
        3,
        "embedding max_n stored",
    )

    expect_error(
        ValueError,
        lambda: (
            RetrievalEmbeddingConfig(
                dimension=0
            )
        ),
        "zero embedding dimension rejected",
    )


def test_chunking_config():
    config = (
        RetrievalChunkingConfig(
            max_chars=200,
            overlap_chars=50,
            min_chunk_chars=20,
        )
    )

    eq(
        config.overlap_chars,
        50,
        "chunk overlap stored",
    )

    expect_error(
        ValueError,
        lambda: (
            RetrievalChunkingConfig(
                max_chars=100,
                overlap_chars=100,
            )
        ),
        "chunk overlap cannot equal max chars",
    )


def test_search_config():
    config = (
        RetrievalSearchConfig(
            top_k=3,
            search_k=2,
            mmr_lambda=0.5,
        )
    )

    eq(
        config.top_k,
        3,
        "search top_k stored",
    )

    result = (
        RetrievalConfigValidator()
        .validate(
            RetrievalConfig(
                search=config
            )
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
        "SEARCH_K_BELOW_TOP_K"
        in codes,
        "search_k/top_k mismatch warned",
    )


def test_codec():
    text = (
        '{"embedding":{'
        '"dimension":512,"min_n":1,"max_n":2,'
        '"use_idf":true,"sublinear_tf":true,"l2_normalize":true'
        '},'
        '"chunking":{'
        '"max_chars":900,"overlap_chars":50,"min_chunk_chars":50'
        '},'
        '"search":{'
        '"top_k":3,"search_k":8,"use_mmr":true,'
        '"mmr_lambda":0.7,"similarity_weight":1.0,'
        '"dataset_boosts":{"siresoft":0.2}'
        '},'
        '"default_index_mode":"replace",'
        '"default_refit":true,'
        '"metadata":{"name":"production"}'
        '}'
    )

    config = (
        RetrievalConfigCodec()
        .decode_text(
            text
        )
    )

    eq(
        config.embedding.dimension,
        512,
        "codec embedding dimension",
    )

    eq(
        config.chunking.max_chars,
        900,
        "codec chunk size",
    )

    eq(
        config.search.dataset_boosts[
            "siresoft"
        ],
        0.2,
        "codec dataset boost",
    )


def test_factory_real_index():
    config = sample_config()

    manager = (
        RetrievalConfigFactory()
        .initialize(
            config,
            build_tokenizer(),
            documents=documents(),
        )
    )

    status = manager.status()

    eq(
        status[
            "documents"
        ],
        3,
        "configured manager indexes documents",
    )

    eq(
        status[
            "index_entries"
        ],
        3,
        "configured manager creates vector index entries",
    )

    eq(
        status[
            "dimension"
        ],
        512,
        "configured embedding dimension applied",
    )

    eq(
        status[
            "idf_fitted"
        ],
        True,
        "configured IDF fitting applied",
    )


def test_factory_search():
    config = sample_config()

    manager = (
        RetrievalConfigFactory()
        .initialize(
            config,
            build_tokenizer(),
            documents=documents(),
        )
    )

    result = (
        RetrievalConfigFactory()
        .search(
            manager,
            config,
            (
                "professional software engineering "
                "and custom applications"
            ),
        )
    )

    eq(
        result.top_k,
        2,
        "configured top_k applied",
    )

    check(
        len(
            result.hits
        ) >= 1,
        "configured search returns hit",
    )

    eq(
        result.hits[
            0
        ].document_id,
        "sire-company",
        "SireSoft document ranks first for software-service query",
    )

    check(
        "dataset_boost=0.1"
        in result.hits[
            0
        ].reasons,
        "configured dataset boost applied transparently",
    )

    check(
        "metadata:priority=0.05"
        in result.hits[
            0
        ].reasons,
        "configured metadata boost applied transparently",
    )


def test_search_override():
    config = sample_config()

    manager = (
        RetrievalConfigFactory()
        .initialize(
            config,
            build_tokenizer(),
            documents=documents(),
        )
    )

    result = (
        RetrievalConfigFactory()
        .search(
            manager,
            config,
            "machine learning artificial intelligence",
            overrides={
                "top_k": 1,
                "search_k": 3,
                "use_mmr": False,
            },
        )
    )

    eq(
        len(
            result.hits
        ),
        1,
        "retrieval override changes top_k",
    )

    eq(
        result.hits[
            0
        ].document_id,
        "ai",
        "retrieval override still returns relevant AI document",
    )

    expect_error(
        ValueError,
        lambda: (
            RetrievalConfigFactory()
            .search(
                manager,
                config,
                "query",
                overrides={
                    "unknown": 1,
                },
            )
        ),
        "unknown retrieval override rejected",
    )


def test_service_creation():
    service = (
        RetrievalConfigFactory()
        .build_service(
            sample_config(),
            build_tokenizer(),
        )
    )

    check(
        isinstance(
            service,
            RetrievalService,
        ),
        "factory creates retrieval service",
    )

    response = service.handle(
        ServiceRequest(
            request_id="status-1",
            service="retrieval_service",
            operation="status",
        )
    )

    eq(
        response.success,
        True,
        "configured retrieval service responds",
    )

    eq(
        response.data[
            "status"
        ][
            "documents"
        ],
        0,
        "new configured retrieval service starts empty",
    )


def test_no_idf_refit_warning():
    config = RetrievalConfig(
        embedding=(
            RetrievalEmbeddingConfig(
                use_idf=False
            )
        ),
        default_refit=True,
    )

    result = (
        RetrievalConfigValidator()
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
        "REFIT_WITHOUT_IDF"
        in codes,
        "refit-without-IDF warning emitted",
    )


def main():
    test_embedding_config()
    test_chunking_config()
    test_search_config()
    test_codec()
    test_factory_real_index()
    test_factory_search()
    test_search_override()
    test_service_creation()
    test_no_idf_refit_warning()

    print(
        "RETRIEVAL CONFIG TEST SUITE: PASS"
    )
    print(
        "Assertions passed:",
        ASSERTIONS,
    )
    print(
        "Files validated: 7/7"
    )
    print(
        "Typed embedding/chunking/search configuration: VALIDATED"
    )
    print(
        "Handwritten JSON decoding: VALIDATED"
    )
    print(
        "RetrievalManager generation: VALIDATED"
    )
    print(
        "Real chunk/embed/index pipeline: VALIDATED"
    )
    print(
        "IDF fitting and exact vector indexing: VALIDATED"
    )
    print(
        "Configured reranking/MMR boosts: VALIDATED"
    )
    print(
        "Search override validation: VALIDATED"
    )
    print(
        "RetrievalService generation: VALIDATED"
    )
    print(
        "Third-party dependencies: 0"
    )


main()
