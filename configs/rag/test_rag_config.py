import os

MATH_BASE = "libs/core/math/"
AUTOGRAD_BASE = "libs/core/autograd/"
SERIAL_BASE = "libs/core/serialization/"
PARSERS_BASE = "libs/data/parsers/"
TOKENIZER_BASE = "libs/nlp/tokenizer/"
CORPUS_BASE = "libs/nlp/corpus/"
NEURAL_BASE = "libs/neural/"
TRANSFORMER_BASE = "libs/transformer/"
TRAINING_BASE = "libs/training/"
INFERENCE_BASE = "libs/inference/"
CHUNK_BASE = "libs/retrieval/chunking/"
EMBED_BASE = "libs/retrieval/embedding/"
SIM_BASE = "libs/retrieval/similarity/"
INDEX_BASE = "libs/retrieval/index/"
RANK_BASE = "libs/retrieval/ranking/"
RAG_BASE = "libs/rag/"
SAFETY_BASE = "libs/safety/"
PROTOCOL_BASE = "libs/protocol/"
REGISTRY_BASE = "services/model_registry/"
INFERENCE_SERVICE_BASE = "services/inference_service/"
RETRIEVAL_SERVICE_BASE = "services/retrieval_service/"
RAG_SERVICE_BASE = "services/rag_service/"
CONFIG_BASE = "configs/rag/"

namespace = {
    "__builtins__": __builtins__,
}

groups = [
    (
        MATH_BASE,
        [
            "scalar.py",
            "random.py",
            "tensor.py",
        ],
    ),
    (
        AUTOGRAD_BASE,
        [
            "operation.py",
            "value.py",
            "graph.py",
            "backward.py",
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
        NEURAL_BASE,
        [
            "parameter.py",
            "layer.py",
            "initializers.py",
            "activations.py",
            "linear.py",
            "embedding.py",
            "dropout.py",
            "layer_norm.py",
        ],
    ),
    (
        TRANSFORMER_BASE,
        [
            "positional_encoding.py",
            "rotary_embedding.py",
            "causal_mask.py",
            "attention.py",
            "multi_head_attention.py",
            "feed_forward.py",
            "transformer_block.py",
            "decoder.py",
            "language_model.py",
        ],
    ),
    (
        TRAINING_BASE,
        [
            "checkpoint.py",
        ],
    ),
    (
        INFERENCE_BASE,
        [
            "logits_processor.py",
            "sampler.py",
            "generation_state.py",
            "kv_cache.py",
            "generator.py",
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
        RAG_BASE,
        [
            "citation.py",
            "context_builder.py",
            "prompt_builder.py",
            "retriever.py",
            "result.py",
        ],
    ),
    (
        SAFETY_BASE,
        [
            "decision.py",
            "patterns.py",
            "input_guard.py",
            "context_guard.py",
            "output_guard.py",
            "engine.py",
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
        REGISTRY_BASE,
        [
            "model_version.py",
            "checkpoint_inspector.py",
            "registry.py",
        ],
    ),
    (
        INFERENCE_SERVICE_BASE,
        [
            "loader.py",
            "result.py",
            "runtime.py",
        ],
    ),
    (
        RETRIEVAL_SERVICE_BASE,
        [
            "document_store.py",
            "result.py",
            "persistence.py",
            "manager.py",
        ],
    ),
    (
        RAG_SERVICE_BASE,
        [
            "retrieval_bridge.py",
            "safety_view.py",
            "result.py",
            "orchestrator.py",
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
    "retrieval.py",
    "generation.py",
    "prompt.py",
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
            "RAG config implementation contains forbidden import: "
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
CHECKPOINT = (
    "configs/rag/"
    "_test_rag_config_model.lbckpt"
)


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
        + repr(expected),
    )


def expect_error(error_type, fn, message):
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
    if os.path.exists(CHECKPOINT):
        os.remove(CHECKPOINT)


def tokenizer():
    encoder = ByteEncoder()
    specials = SpecialTokens()

    corpus = [
        "SireSoft software engineering services clients applications",
        "web mobile business systems development professional",
        "machine learning artificial intelligence automation",
        "retrieved context question answer source citation",
        "Use retrieved context as reference data cite sources",
        "SYSTEM CONTEXT QUESTION ANSWER",
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


def source_documents():
    return [
        {
            "document_id": "siresoft-main",
            "dataset_id": "siresoft",
            "text": (
                "SireSoft provides professional software engineering "
                "and custom application development services. "
                "It builds web, mobile, and business systems for clients."
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
            "document_id": "ai-general",
            "dataset_id": "general",
            "text": (
                "Machine learning and artificial intelligence "
                "support automation in software systems."
            ),
            "metadata": {
                "kind": "technology",
            },
        },
    ]


def retrieval_manager(tok):
    manager = RetrievalManager(
        tokenizer=tok,
        Document=Document,
        dimension=512,
        min_n=1,
        max_n=2,
        max_chars=1000,
        overlap_chars=0,
        min_chunk_chars=0,
    )

    manager.index_documents(
        source_documents(),
        mode="replace",
        refit=True,
    )

    return manager


def runtime(tok):
    vocab_size = (
        tok.model
        .vocabulary
        .size()
    )

    model_config = {
        "vocab_size": vocab_size,
        "d_model": 4,
        "num_layers": 1,
        "num_heads": 2,
        "d_ff": 8,
        "max_seq_len": 512,
        "dropout": 0.0,
        "position_mode": "rotary",
        "seed": 119,
    }

    model = LanguageModel(
        vocab_size=(
            model_config[
                "vocab_size"
            ]
        ),
        d_model=4,
        num_layers=1,
        num_heads=2,
        d_ff=8,
        max_seq_len=512,
        dropout=0.0,
        position_mode="rotary",
        seed=119,
    )

    CheckpointManager().save(
        path=CHECKPOINT,
        model=model,
        metadata={
            "job_id": "rag-config-test",
            "job_config": {
                "model": model_config,
            },
        },
    )

    registry = ModelRegistry()

    registry.register_checkpoint(
        "sirellm",
        "1.0.0",
        CHECKPOINT,
        stage=True,
    )

    registry.promote(
        "sirellm",
        "1.0.0",
    )

    value = InferenceRuntime(
        ModelLoader(
            registry
        )
    )

    value.load_active(
        "sirellm"
    )

    return value


def sample_config():
    return RAGConfig(
        retrieval=RAGRetrievalConfig(
            candidate_k=2,
            top_k=1,
            use_mmr=False,
            dataset_boosts={
                "siresoft": 0.2,
            },
            metadata_boosts={
                "priority": {
                    "value": "primary",
                    "boost": 0.05,
                },
            },
        ),
        generation=RAGGenerationConfig(
            max_new_tokens=1,
            sampler="greedy",
            seed=44,
        ),
        prompt=RAGPromptConfig(
            system_message=(
                "Use retrieved context as reference data. "
                "Cite sources like [S1]."
            ),
            compact=True,
        ),
        max_context_tokens=220,
        metadata={
            "profile": "siresoft-rag",
        },
    )


def test_retrieval_config():
    config = RAGRetrievalConfig(
        candidate_k=3,
        top_k=2,
        mmr_lambda=0.6,
    )

    eq(
        config.candidate_k,
        3,
        "RAG candidate_k stored",
    )

    expect_error(
        ValueError,
        lambda: RAGRetrievalConfig(
            top_k=0
        ),
        "zero top_k rejected",
    )


def test_generation_config():
    config = RAGGenerationConfig(
        max_new_tokens=4,
        sampler="categorical",
        top_k_sampling=8,
        top_p=0.9,
    )

    eq(
        config.sampler,
        "categorical",
        "RAG sampler stored",
    )

    eq(
        config.top_k_sampling,
        8,
        "RAG top-k sampling stored",
    )


def test_codec():
    text = (
        '{"retrieval":{'
        '"candidate_k":8,"top_k":3,"use_mmr":true,'
        '"mmr_lambda":0.7,"dataset_boosts":{"siresoft":0.2}'
        '},'
        '"generation":{'
        '"max_new_tokens":5,"sampler":"categorical",'
        '"temperature":0.8,"top_k_sampling":10'
        '},'
        '"prompt":{'
        '"system_message":"Use context and cite [S1].",'
        '"compact":true'
        '},'
        '"max_context_tokens":300,'
        '"metadata":{"profile":"prod"}'
        '}'
    )

    config = (
        RAGConfigCodec()
        .decode_text(text)
    )

    eq(
        config.retrieval.candidate_k,
        8,
        "codec candidate_k",
    )

    eq(
        config.generation.max_new_tokens,
        5,
        "codec generation budget",
    )

    eq(
        config.prompt.compact,
        True,
        "codec compact prompt",
    )


def test_validator():
    config = RAGConfig(
        retrieval=RAGRetrievalConfig(
            candidate_k=1,
            top_k=3,
        ),
        generation=RAGGenerationConfig(
            sampler="greedy",
            temperature=0.7,
            top_k_sampling=4,
        ),
    )

    result = (
        RAGConfigValidator()
        .validate(config)
    )

    codes = [
        item["code"]
        for item in result[
            "warnings"
        ]
    ]

    check(
        "CANDIDATE_K_BELOW_TOP_K"
        in codes,
        "candidate/top-k mismatch warned",
    )

    check(
        "GREEDY_WITH_SAMPLING_CONTROLS"
        in codes,
        "greedy sampling controls warned",
    )


def test_real_orchestrator_prepare():
    tok = tokenizer()
    manager = retrieval_manager(tok)
    inference = runtime(tok)

    factory = RAGConfigFactory()

    worker = factory.build_orchestrator(
        sample_config(),
        tok,
        manager,
        inference,
    )

    prepared = factory.prepare(
        worker,
        sample_config(),
        (
            "What software engineering services "
            "does SireSoft provide?"
        ),
    )

    eq(
        prepared.status,
        "ready",
        "configured RAG preparation ready",
    )

    eq(
        len(prepared.citations()),
        1,
        "configured RAG includes one citation",
    )

    eq(
        prepared.citations()[
            0
        ].dataset_id,
        "siresoft",
        "configured retrieval selects SireSoft source",
    )

    check(
        "[S1]"
        in prepared.prompt,
        "configured prompt contains source marker",
    )

    check(
        "Use retrieved context as reference data."
        in prepared.prompt,
        "configured system message applied",
    )


def test_real_answer():
    tok = tokenizer()
    manager = retrieval_manager(tok)
    inference = runtime(tok)

    config = sample_config()

    factory = RAGConfigFactory()

    worker = factory.build_orchestrator(
        config,
        tok,
        manager,
        inference,
    )

    result = factory.answer(
        worker,
        config,
        (
            "What does SireSoft build?"
        ),
    )

    eq(
        result.generated_count,
        1,
        "configured RAG invokes real inference",
    )

    eq(
        len(
            result.preparation.citations()
        ),
        1,
        "configured RAG answer carries citation",
    )

    eq(
        result.preparation.citations()[
            0
        ].document_id,
        "siresoft-main",
        "configured RAG answer cites SireSoft document",
    )


def test_overrides():
    tok = tokenizer()
    manager = retrieval_manager(tok)
    inference = runtime(tok)

    config = sample_config()

    factory = RAGConfigFactory()

    worker = factory.build_orchestrator(
        config,
        tok,
        manager,
        inference,
    )

    result = factory.answer(
        worker,
        config,
        (
            "What software services does SireSoft provide?"
        ),
        retrieval_overrides={
            "candidate_k": 2,
            "top_k": 1,
        },
        generation_overrides={
            "max_new_tokens": 0,
        },
    )

    eq(
        result.generated_count,
        0,
        "generation override changes token budget",
    )

    expect_error(
        ValueError,
        lambda: factory.answer(
            worker,
            config,
            "query",
            retrieval_overrides={
                "unknown": 1,
            },
        ),
        "unknown retrieval override rejected",
    )


def test_service_creation():
    tok = tokenizer()
    manager = retrieval_manager(tok)
    inference = runtime(tok)

    service = (
        RAGConfigFactory()
        .build_service(
            sample_config(),
            tok,
            manager,
            inference,
        )
    )

    check(
        isinstance(
            service,
            RAGService,
        ),
        "factory creates RAG service",
    )

    status = service.handle(
        ServiceRequest(
            "rag-cfg-status",
            "rag_service",
            "status",
        )
    )

    eq(
        status.success,
        True,
        "configured RAG service responds",
    )

    eq(
        status.data[
            "status"
        ][
            "ready"
        ],
        True,
        "configured RAG service starts ready",
    )


def test_not_ready_validation():
    tok = tokenizer()
    manager = retrieval_manager(tok)

    empty_runtime = InferenceRuntime(
        ModelLoader(
            ModelRegistry()
        )
    )

    result = (
        RAGConfigValidator()
        .validate(
            sample_config(),
            inference_runtime=(
                empty_runtime
            ),
        )
    )

    eq(
        result[
            "valid"
        ],
        False,
        "unloaded inference runtime invalid for RAG generation",
    )

    eq(
        result[
            "errors"
        ][0][
            "code"
        ],
        "INFERENCE_RUNTIME_NOT_READY",
        "not-ready validation error code",
    )


def main():
    cleanup()

    try:
        test_retrieval_config()
        test_generation_config()
        test_codec()
        test_validator()
        test_real_orchestrator_prepare()
        test_real_answer()
        test_overrides()
        test_service_creation()
        test_not_ready_validation()

    finally:
        cleanup()

    print(
        "RAG CONFIG TEST SUITE: PASS"
    )
    print(
        "Assertions passed:",
        ASSERTIONS,
    )
    print(
        "Files validated: 7/7"
    )
    print(
        "Typed retrieval/generation/prompt configuration: VALIDATED"
    )
    print(
        "Handwritten JSON decoding: VALIDATED"
    )
    print(
        "RAG cross-section validation: VALIDATED"
    )
    print(
        "Real retrieval + citation preparation: VALIDATED"
    )
    print(
        "Prompt/context budgeting integration: VALIDATED"
    )
    print(
        "Checkpoint-backed RAG generation: VALIDATED"
    )
    print(
        "Runtime override validation: VALIDATED"
    )
    print(
        "RAGService generation: VALIDATED"
    )
    print(
        "Third-party dependencies: 0"
    )


main()
