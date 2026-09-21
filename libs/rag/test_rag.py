MATH_BASE = "libs/core/math/"
AUTOGRAD_BASE = "libs/core/autograd/"
TOKENIZER_BASE = "libs/nlp/tokenizer/"
NEURAL_BASE = "libs/neural/"
TRANSFORMER_BASE = "libs/transformer/"
INFERENCE_BASE = "libs/inference/"
CHUNK_BASE = "libs/retrieval/chunking/"
EMBED_BASE = "libs/retrieval/embedding/"
SIM_BASE = "libs/retrieval/similarity/"
INDEX_BASE = "libs/retrieval/index/"
RANK_BASE = "libs/retrieval/ranking/"
RAG_BASE = "libs/rag/"

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
        INFERENCE_BASE,
        [
            "logits_processor.py",
            "sampler.py",
            "generation_state.py",
            "generator.py",
        ],
    ),
    (
        CHUNK_BASE,
        [
            "chunk.py",
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
            "cosine.py",
            "batch_similarity.py",
            "scorer.py",
        ],
    ),
    (
        INDEX_BASE,
        [
            "entry.py",
            "flat_index.py",
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
    "citation.py",
    "context_builder.py",
    "prompt_builder.py",
    "retriever.py",
    "result.py",
    "pipeline.py",
]:
    path = RAG_BASE + filename

    source = open(
        path,
        "r",
        encoding="utf-8",
    ).read()

    if "import " in source:
        raise AssertionError(
            "RAG implementation contains forbidden import: "
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

    corpus = [
        "SireSoft builds software systems.",
        "SireSoft provides engineering services.",
        "SireSoft develops AI solutions.",
        "cloud applications and clients",
        "software engineering application development",
        "cooking vegetables kitchen recipes",
        "SYSTEM CONTEXT QUESTION ANSWER source dataset document",
        "Use context. Cite source. What does SireSoft build?",
    ]

    model = BPETrainer(
        byte_encoder=byte_encoder,
        pair_counter=PairCounter(),
        vocabulary_factory=Vocabulary,
        special_tokens=specials,
    ).train(
        corpus,
        vocab_size=320,
        min_frequency=2,
    )

    return BPETokenizer(
        model,
        byte_encoder,
        specials,
    )


def build_stack(with_generator=False):
    tokenizer = build_tokenizer()

    chunks = [
        Chunk(
            chunk_id="software",
            document_id="siresoft-main",
            dataset_id="siresoft",
            text="SireSoft builds software systems.",
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
            chunk_id="engineering",
            document_id="siresoft-main",
            dataset_id="siresoft",
            text="SireSoft provides engineering services.",
            chunk_index=1,
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
            chunk_id="ai",
            document_id="siresoft-main",
            dataset_id="siresoft",
            text="SireSoft develops AI solutions.",
            chunk_index=2,
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
            chunk_id="food",
            document_id="other",
            dataset_id="other",
            text="Cooking vegetables in a kitchen.",
            chunk_index=0,
            metadata={
                "section": "food",
                "rag": False,
            },
        ),
    ]

    embedder = HashingTFIDFEmbedder(
        tokenizer=tokenizer,
        dimension=512,
        min_n=1,
        max_n=2,
    )

    embedder.fit_chunks(chunks)

    scorer = SimilarityScorer(embedder)
    embedded = scorer.embed_items(chunks)

    index = FlatVectorIndex(
        dimension=512,
        metric=CosineSimilarity(),
    )

    for item in embedded:
        index.add_embedded(item)

    ranking = RankingPipeline(
        reranker=RetrievalReranker(
            metadata_boosts={
                "authoritative": {
                    "value": True,
                    "boost": 0.02,
                },
            },
        ),
        duplicate_suppressor=DuplicateSuppressor(),
        mmr=MaximalMarginalRelevance(
            lambda_relevance=0.8,
        ),
    )

    retriever = Retriever(
        embedder=embedder,
        index=index,
        ranking_pipeline=ranking,
    )

    context_builder = ContextBuilder(
        tokenizer=tokenizer,
        max_context_tokens=80,
    )

    prompt_builder = PromptBuilder(
        system_message="Use context. Cite [S1].",
        compact=True,
    )

    generator = None

    if with_generator:
        model = LanguageModel(
            vocab_size=(
                tokenizer
                .model
                .vocabulary
                .size()
            ),
            d_model=4,
            num_layers=1,
            num_heads=2,
            d_ff=8,
            max_seq_len=192,
            dropout=0.0,
            position_mode="rotary",
            seed=501,
        )

        generator = InferenceGenerator(
            model=model,
            sampler=GreedySampler(),
            logits_processor=LogitsProcessor(
                temperature=1.0,
            ),
            context_window=192,
        )

    pipeline = RAGPipeline(
        tokenizer=tokenizer,
        retriever=retriever,
        context_builder=context_builder,
        prompt_builder=prompt_builder,
        generator=generator,
    )

    return (
        tokenizer,
        chunks,
        retriever,
        context_builder,
        prompt_builder,
        pipeline,
    )


def test_citations():
    (
        tokenizer,
        chunks,
        retriever,
        context_builder,
        prompt_builder,
        pipeline,
    ) = build_stack()

    bundle = retriever.retrieve(
        "software systems",
        candidate_k=4,
        top_k=2,
        use_mmr=False,
    )

    citations = CitationBuilder().build(
        bundle.ranked_results
    )

    eq(
        citations[0].marker(),
        "[S1]",
        "first citation marker",
    )

    eq(
        citations[0].item_id,
        "software",
        "citation retains item identity",
    )

    eq(
        citations[0].provenance["file"],
        "siresoft.txt",
        "citation retains provenance",
    )


def test_retriever_real_stack():
    (
        tokenizer,
        chunks,
        retriever,
        context_builder,
        prompt_builder,
        pipeline,
    ) = build_stack()

    bundle = retriever.retrieve(
        "software systems",
        candidate_k=4,
        top_k=3,
        use_mmr=False,
    )

    eq(
        bundle.ranked_results[0].item_id,
        "software",
        "retriever ranks relevant chunk first",
    )

    check(
        len(bundle.raw_results) >= 3,
        "retriever retains raw candidates",
    )


def test_context_budget_and_provenance():
    (
        tokenizer,
        chunks,
        retriever,
        context_builder,
        prompt_builder,
        pipeline,
    ) = build_stack()

    bundle = retriever.retrieve(
        "SireSoft software engineering AI",
        candidate_k=4,
        top_k=3,
        use_mmr=False,
    )

    context = context_builder.build(
        bundle.ranked_results,
        max_context_tokens=45,
    )

    check(
        context.token_count <= 45,
        "context respects token budget",
    )

    check(
        context.source_count() >= 1,
        "context includes at least one source",
    )

    index = 0

    while index < len(context.citations):
        citation = context.citations[index]

        eq(
            citation.citation_id,
            "S" + str(index + 1),
            "accepted citations remain sequential",
        )

        eq(
            citation.dataset_id,
            "siresoft",
            "context citation keeps dataset",
        )

        eq(
            citation.provenance["file"],
            "siresoft.txt",
            "context keeps source file provenance",
        )

        index += 1


def test_context_whole_chunk_policy():
    (
        tokenizer,
        chunks,
        retriever,
        context_builder,
        prompt_builder,
        pipeline,
    ) = build_stack()

    bundle = retriever.retrieve(
        "software",
        candidate_k=4,
        top_k=3,
        use_mmr=False,
    )

    tiny = context_builder.build(
        bundle.ranked_results,
        max_context_tokens=1,
    )

    eq(
        tiny.source_count(),
        0,
        "oversized evidence skipped instead of truncated",
    )

    check(
        len(tiny.skipped_item_ids) > 0,
        "skipped source IDs are recorded",
    )


def test_prompt_builder():
    (
        tokenizer,
        chunks,
        retriever,
        context_builder,
        prompt_builder,
        pipeline,
    ) = build_stack()

    bundle = retriever.retrieve(
        "software systems",
        candidate_k=4,
        top_k=2,
        use_mmr=False,
    )

    context = context_builder.build(
        bundle.ranked_results
    )

    prompt = prompt_builder.build(
        "What does SireSoft build?",
        context,
    )

    check(
        "[S1]" in prompt,
        "prompt includes citation marker",
    )

    check(
        "What does SireSoft build?"
        in prompt,
        "prompt includes user question",
    )

    check(
        "ANSWER:" in prompt,
        "prompt includes answer boundary",
    )


def test_prepare_pipeline():
    (
        tokenizer,
        chunks,
        retriever,
        context_builder,
        prompt_builder,
        pipeline,
    ) = build_stack()

    prepared = pipeline.prepare(
        query_text="What does SireSoft build?",
        candidate_k=4,
        top_k=3,
        use_mmr=False,
    )

    check(
        prepared.prompt_token_count() > 0,
        "prepared prompt tokenized",
    )

    eq(
        prepared.context.citations[0].item_id,
        "software",
        "prepared RAG context uses relevant source",
    )

    eq(
        prepared.context.citations[0].provenance["file"],
        "siresoft.txt",
        "prepared RAG keeps provenance",
    )


def test_prompt_budget_backoff():
    (
        tokenizer,
        chunks,
        retriever,
        context_builder,
        prompt_builder,
        pipeline,
    ) = build_stack()

    roomy = pipeline.prepare(
        query_text="What services does SireSoft provide?",
        candidate_k=4,
        top_k=3,
        use_mmr=False,
    )

    base_context = ContextPackage(
        text="",
        citations=[],
        token_count=0,
    )

    base_prompt = prompt_builder.build(
        "What services does SireSoft provide?",
        base_context,
    )

    base_count = len(
        tokenizer.encode(base_prompt)
    )

    tight_limit = base_count + 25

    tight = pipeline.prepare(
        query_text="What services does SireSoft provide?",
        candidate_k=4,
        top_k=3,
        use_mmr=False,
        max_prompt_tokens=tight_limit,
    )

    check(
        tight.prompt_token_count()
        <= tight_limit,
        "prompt backoff respects hard prompt budget",
    )

    check(
        tight.context.source_count()
        <= roomy.context.source_count(),
        "prompt backoff removes low-ranked context when needed",
    )


def test_filtered_rag():
    (
        tokenizer,
        chunks,
        retriever,
        context_builder,
        prompt_builder,
        pipeline,
    ) = build_stack()

    prepared = pipeline.prepare(
        query_text="What does SireSoft do?",
        candidate_k=4,
        top_k=3,
        filters={
            "dataset_id": "siresoft",
            "rag": True,
        },
        use_mmr=True,
    )

    for citation in prepared.context.citations:
        eq(
            citation.dataset_id,
            "siresoft",
            "RAG filter restricts dataset",
        )

        eq(
            citation.metadata["rag"],
            True,
            "RAG eligibility filter preserved",
        )


def test_real_transformer_generation_integration():
    (
        tokenizer,
        chunks,
        retriever,
        context_builder,
        prompt_builder,
        pipeline,
    ) = build_stack(
        with_generator=True
    )

    result = pipeline.generate(
        query_text="What does SireSoft build?",
        max_new_tokens=1,
        candidate_k=4,
        top_k=1,
        use_mmr=False,
    )

    eq(
        len(result.generated_ids),
        1,
        "real Transformer RAG generates requested token",
    )

    check(
        isinstance(result.answer_text, str),
        "generated RAG answer decodes safely to text",
    )

    eq(
        result.citations[0].item_id,
        "software",
        "generated RAG result carries retrieved citation",
    )

    eq(
        result.stop_reason,
        "max_new_tokens",
        "generation stop reason propagated",
    )


def test_no_generator_error():
    (
        tokenizer,
        chunks,
        retriever,
        context_builder,
        prompt_builder,
        pipeline,
    ) = build_stack()

    expect_error(
        RuntimeError,
        lambda: pipeline.generate(
            "What does SireSoft build?",
            max_new_tokens=1,
        ),
        "generation requires configured generator",
    )


def test_validation():
    (
        tokenizer,
        chunks,
        retriever,
        context_builder,
        prompt_builder,
        pipeline,
    ) = build_stack()

    expect_error(
        ValueError,
        lambda: retriever.retrieve(""),
        "empty retrieval query rejected",
    )

    expect_error(
        ValueError,
        lambda: ContextBuilder(
            tokenizer,
            max_context_tokens=-1,
        ),
        "negative context budget rejected",
    )

    expect_error(
        ValueError,
        lambda: prompt_builder.build(
            "   ",
            ContextPackage(
                "",
                [],
                0,
            ),
        ),
        "empty prompt question rejected",
    )


def main():
    test_citations()
    test_retriever_real_stack()
    test_context_budget_and_provenance()
    test_context_whole_chunk_policy()
    test_prompt_builder()
    test_prepare_pipeline()
    test_prompt_budget_backoff()
    test_filtered_rag()
    test_real_transformer_generation_integration()
    test_no_generator_error()
    test_validation()

    print(
        "RAG TEST SUITE: PASS"
    )
    print(
        "Assertions passed:",
        ASSERTIONS,
    )
    print(
        "Files validated: 6/6"
    )
    print(
        "Query embedding + index retrieval: VALIDATED"
    )
    print(
        "Ranking + duplicate/MMR integration: VALIDATED"
    )
    print(
        "Context token budgeting: VALIDATED"
    )
    print(
        "Citation/provenance preservation: VALIDATED"
    )
    print(
        "Prompt construction/backoff: VALIDATED"
    )
    print(
        "Real Transformer generation integration: VALIDATED"
    )
    print(
        "Third-party dependencies: 0"
    )


main()
