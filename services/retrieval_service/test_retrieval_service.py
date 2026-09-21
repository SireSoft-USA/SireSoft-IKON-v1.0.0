import os

MATH_BASE = "libs/core/math/"
SERIAL_BASE = "libs/core/serialization/"
TOKENIZER_BASE = "libs/nlp/tokenizer/"
CORPUS_BASE = "libs/nlp/corpus/"
CHUNK_BASE = "libs/retrieval/chunking/"
EMBED_BASE = "libs/retrieval/embedding/"
SIM_BASE = "libs/retrieval/similarity/"
INDEX_BASE = "libs/retrieval/index/"
RANK_BASE = "libs/retrieval/ranking/"
PROTOCOL_BASE = "libs/protocol/"
SERVICE_BASE = "services/retrieval_service/"

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
    "document_store.py",
    "result.py",
    "persistence.py",
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
            "retrieval_service implementation contains forbidden import: "
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
    "services/retrieval_service/"
    "_test_retrieval.slretr"
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
    encoder = ByteEncoder()
    specials = SpecialTokens()

    if variant == 1:
        corpus = [
            "SireSoft software engineering development services",
            "custom applications web mobile cloud systems",
            "machine learning artificial intelligence software",
            "cooking recipes vegetables kitchen dinner",
            "students university courses education learning",
            "client projects professional development support",
        ]
    else:
        corpus = [
            "totally unrelated vocabulary corpus",
            "music travel cinema gardening",
            "another tokenizer merge sequence",
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
                "The company builds web, mobile, and business systems."
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
            "document_id": "cooking",
            "dataset_id": "general",
            "text": (
                "A cooking recipe uses vegetables, a kitchen, "
                "heat, spices, and dinner ingredients."
            ),
            "metadata": {
                "kind": "food",
            },
            "provenance": {
                "source_file": "food.txt",
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
            "provenance": {
                "source_file": "ai.txt",
            },
        },
        {
            "document_id": "sire-duplicate",
            "dataset_id": "mirror",
            "text": (
                "SireSoft provides professional software engineering "
                "and custom application development services for clients. "
                "The company builds web, mobile, and business systems."
            ),
            "metadata": {
                "kind": "mirror",
            },
            "provenance": {
                "source_file": "mirror.txt",
            },
        },
    ]


def manager(
    tokenizer=None,
):
    if tokenizer is None:
        tokenizer = (
            build_tokenizer()
        )

    return RetrievalManager(
        tokenizer=tokenizer,
        Document=Document,
        dimension=1024,
        min_n=1,
        max_n=2,
        max_chars=1000,
        overlap_chars=0,
        min_chunk_chars=0,
    )


def indexed_manager(
    tokenizer=None,
):
    worker = manager(
        tokenizer=tokenizer
    )

    worker.index_documents(
        documents(),
        mode="replace",
        refit=True,
    )

    return worker


def test_document_store():
    store = RetrievalDocumentStore(
        Document
    )

    store.replace_all(
        documents()[:2]
    )

    eq(
        store.count(),
        2,
        "document store replacement count",
    )

    eq(
        store.get(
            "sire-company"
        ).dataset_id,
        "siresoft",
        "document store payload conversion",
    )

    store.upsert_many(
        [
            {
                "document_id": "sire-company",
                "dataset_id": "siresoft",
                "text": "updated",
            },
            {
                "document_id": "new",
                "dataset_id": "general",
                "text": "new document",
            },
        ]
    )

    eq(
        store.count(),
        3,
        "upsert preserves existing order and adds new document",
    )

    eq(
        store.get(
            "sire-company"
        ).text,
        "updated",
        "upsert updates document",
    )

    store.remove(
        "new"
    )

    eq(
        store.count(),
        2,
        "document removal",
    )


def test_index_build():
    worker = indexed_manager()

    status = worker.status()

    eq(
        status[
            "documents"
        ],
        4,
        "indexed document count",
    )

    eq(
        status[
            "chunks"
        ],
        4,
        "one chunk per test document",
    )

    eq(
        status[
            "index_entries"
        ],
        4,
        "vector index entry count",
    )

    eq(
        status[
            "idf_fitted"
        ],
        True,
        "IDF fitted during index build",
    )

    entry = worker.index.get(
        "sire-company::char::0"
    )

    eq(
        entry.metadata[
            "char_start"
        ],
        0,
        "source char_start preserved into index metadata",
    )

    eq(
        entry.metadata[
            "char_end"
        ],
        len(
            documents()[
                0
            ][
                "text"
            ]
        ),
        "source char_end preserved into index metadata",
    )

    eq(
        entry.provenance[
            "source_file"
        ],
        (
            "datasets/raw/siresoft/"
            "siresoft.txt"
        ),
        "source provenance preserved",
    )


def test_search_ranking_and_dedup():
    worker = indexed_manager()

    result = worker.search(
        "software engineering application development services",
        top_k=3,
        search_k=4,
        use_mmr=False,
    )

    check(
        len(
            result.hits
        ) >= 2,
        "search returns ranked results",
    )

    eq(
        result.hits[
            0
        ].document_id,
        "sire-company",
        "software query ranks SireSoft document first",
    )

    texts = [
        hit.text.lower()
        for hit in result.hits
    ]

    eq(
        len(
            texts
        ),
        len(
            set(
                texts
            )
        ),
        "exact duplicate text suppressed",
    )

    check(
        result.hits[
            0
        ].similarity_score
        > 0.0,
        "top retrieval similarity positive",
    )


def test_filtering():
    worker = indexed_manager()

    result = worker.search(
        "software systems",
        top_k=3,
        filters={
            "dataset_id": "general",
        },
        use_mmr=False,
    )

    check(
        len(
            result.hits
        ) > 0,
        "filtered search returns results",
    )

    for hit in result.hits:
        eq(
            hit.dataset_id,
            "general",
            "dataset filter enforced",
        )


def test_transparent_boost():
    worker = indexed_manager()

    result = worker.search(
        "software",
        top_k=3,
        search_k=4,
        use_mmr=False,
        dataset_boosts={
            "general": 2.0,
        },
    )

    eq(
        result.hits[
            0
        ].dataset_id,
        "general",
        "explicit dataset boost changes ranking",
    )

    check(
        any(
            reason.startswith(
                "dataset_boost="
            )
            for reason
            in result.hits[
                0
            ].reasons
        ),
        "boost reason is transparent",
    )


def test_mmr():
    worker = indexed_manager()

    result = worker.search(
        "software engineering systems",
        top_k=2,
        search_k=4,
        use_mmr=True,
        mmr_lambda=0.6,
    )

    eq(
        len(
            result.hits
        ),
        2,
        "MMR returns requested top k",
    )

    for hit in result.hits:
        check(
            any(
                reason.startswith(
                    "mmr_rank="
                )
                for reason
                in hit.reasons
            ),
            "MMR selection reason recorded",
        )


def test_upsert_refit():
    worker = indexed_manager()

    worker.index_documents(
        [
            {
                "document_id": "cooking",
                "dataset_id": "general",
                "text": (
                    "Software engineering replaces the old "
                    "cooking document content completely."
                ),
                "metadata": {
                    "kind": "changed",
                },
            },
        ],
        mode="upsert",
        refit=True,
    )

    eq(
        worker.document_store.get(
            "cooking"
        ).metadata[
            "kind"
        ],
        "changed",
        "upsert updates source document",
    )

    entry = worker.index.get(
        "cooking::char::0"
    )

    check(
        "Software engineering"
        in entry.text,
        "rebuild indexes updated text",
    )

    eq(
        worker.status()[
            "idf_document_count"
        ],
        4,
        "upsert refit recomputes IDF across full document set",
    )


def test_remove_document():
    worker = indexed_manager()

    worker.remove_document(
        "cooking",
        refit=True,
    )

    eq(
        worker.status()[
            "documents"
        ],
        3,
        "remove document source count",
    )

    check(
        not worker.index.contains(
            "cooking::char::0"
        ),
        "removed document chunk removed from index",
    )

    eq(
        worker.status()[
            "idf_document_count"
        ],
        3,
        "remove refits IDF across remaining chunks",
    )


def test_clear():
    worker = indexed_manager()

    status = worker.clear()

    eq(
        status[
            "documents"
        ],
        0,
        "clear removes documents",
    )

    eq(
        status[
            "index_entries"
        ],
        0,
        "clear removes index entries",
    )

    eq(
        status[
            "idf_fitted"
        ],
        False,
        "clear resets IDF state",
    )


def test_persistence_round_trip():
    if os.path.exists(
        STATE_PATH
    ):
        os.remove(
            STATE_PATH
        )

    tokenizer = (
        build_tokenizer()
    )

    source = indexed_manager(
        tokenizer=tokenizer
    )

    before = source.search(
        "software engineering services",
        top_k=3,
        search_k=4,
        use_mmr=False,
    ).to_dict()

    saved = source.save_state(
        STATE_PATH
    )

    check(
        saved[
            "bytes"
        ] > 0,
        "retrieval state writes bytes",
    )

    restored = manager(
        tokenizer=tokenizer
    )

    loaded = restored.load_state_file(
        STATE_PATH
    )

    eq(
        loaded[
            "documents"
        ],
        4,
        "retrieval state restores documents",
    )

    eq(
        loaded[
            "entries"
        ],
        4,
        "retrieval state restores index",
    )

    after = restored.search(
        "software engineering services",
        top_k=3,
        search_k=4,
        use_mmr=False,
    ).to_dict()

    eq(
        after,
        before,
        "retrieval state preserves exact search results",
    )


def test_persistence_tokenizer_guard():
    tokenizer = (
        build_tokenizer()
    )

    source = indexed_manager(
        tokenizer=tokenizer
    )

    source.save_state(
        STATE_PATH
    )

    wrong = manager(
        tokenizer=build_tokenizer(
            variant=2
        )
    )

    expect_error(
        ValueError,
        lambda: wrong.load_state_file(
            STATE_PATH
        ),
        "retrieval state from different tokenizer rejected",
    )


def test_persistence_corruption():
    tokenizer = (
        build_tokenizer()
    )

    source = indexed_manager(
        tokenizer=tokenizer
    )

    source.save_state(
        STATE_PATH
    )

    handle = open(
        STATE_PATH,
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
        STATE_PATH,
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
        lambda: manager(
            tokenizer=tokenizer
        ).load_state_file(
            STATE_PATH
        ),
        "retrieval snapshot checksum detects corruption",
    )


def test_service_flow():
    service = RetrievalService(
        manager()
    )

    indexed = service.handle(
        ServiceRequest(
            "s1",
            "retrieval_service",
            "index_documents",
            payload={
                "documents": documents(),
            },
        )
    )

    eq(
        indexed.success,
        True,
        "service indexing succeeds",
    )

    searched = service.handle(
        ServiceRequest(
            "s2",
            "retrieval_service",
            "search",
            payload={
                "query": (
                    "software engineering development"
                ),
                "top_k": 2,
                "search_k": 4,
                "use_mmr": False,
            },
        )
    )

    eq(
        searched.success,
        True,
        "service search succeeds",
    )

    eq(
        searched.data[
            "result"
        ][
            "hits"
        ][0][
            "document_id"
        ],
        "sire-company",
        "service retrieves SireSoft source",
    )

    first_hit = searched.data[
        "result"
    ][
        "hits"
    ][0]

    check(
        "vector"
        not in first_hit,
        "default retrieval protocol omits large vector payload",
    )

    eq(
        first_hit[
            "provenance"
        ][
            "source_file"
        ],
        (
            "datasets/raw/siresoft/"
            "siresoft.txt"
        ),
        "service returns source provenance",
    )


def test_service_protocol_round_trip():
    service = RetrievalService(
        manager()
    )

    codec = ProtocolCodec()

    index_request = ServiceRequest(
        "protocol-index",
        "retrieval_service",
        "index_documents",
        payload={
            "documents": documents(),
        },
        trace_id="trace-retrieval",
    )

    index_request = (
        codec.decode_request(
            codec.encode_request(
                index_request
            )
        )
    )

    index_response = (
        service.handle(
            index_request
        )
    )

    index_response = (
        codec.decode_response(
            codec.encode_response(
                index_response
            )
        )
    )

    eq(
        index_response.success,
        True,
        "retrieval indexing survives protocol codec",
    )

    eq(
        index_response.trace_id,
        "trace-retrieval",
        "retrieval trace preserved",
    )

    search_request = (
        ServiceRequest(
            "protocol-search",
            "retrieval_service",
            "search",
            payload={
                "query": (
                    "software engineering services"
                ),
                "top_k": 2,
                "filters": {
                    "dataset_id": "siresoft",
                },
            },
        )
    )

    search_request = (
        codec.decode_request(
            codec.encode_request(
                search_request
            )
        )
    )

    search_response = (
        service.handle(
            search_request
        )
    )

    search_response = (
        codec.decode_response(
            codec.encode_response(
                search_response
            )
        )
    )

    eq(
        search_response.success,
        True,
        "retrieval search survives protocol codec",
    )

    eq(
        search_response.data[
            "result"
        ][
            "hits"
        ][0][
            "dataset_id"
        ],
        "siresoft",
        "protocol filter preserved",
    )


def test_service_state():
    if os.path.exists(
        STATE_PATH
    ):
        os.remove(
            STATE_PATH
        )

    tokenizer = (
        build_tokenizer()
    )

    source_service = RetrievalService(
        manager(
            tokenizer=tokenizer
        )
    )

    source_service.handle(
        ServiceRequest(
            "i",
            "retrieval_service",
            "index_documents",
            payload={
                "documents": documents(),
            },
        )
    )

    saved = source_service.handle(
        ServiceRequest(
            "save",
            "retrieval_service",
            "save_state",
            payload={
                "path": STATE_PATH,
            },
        )
    )

    eq(
        saved.success,
        True,
        "service saves retrieval state",
    )

    target_service = RetrievalService(
        manager(
            tokenizer=tokenizer
        )
    )

    loaded = target_service.handle(
        ServiceRequest(
            "load",
            "retrieval_service",
            "load_state",
            payload={
                "path": STATE_PATH,
            },
        )
    )

    eq(
        loaded.success,
        True,
        "service loads retrieval state",
    )

    eq(
        loaded.data[
            "status"
        ][
            "entries"
        ],
        4,
        "service restored entry count",
    )


def test_errors():
    service = RetrievalService(
        manager()
    )

    wrong = service.handle(
        ServiceRequest(
            "w",
            "rag_service",
            "status",
        )
    )

    eq(
        wrong.error.code,
        "INVALID_REQUEST",
        "wrong target service rejected",
    )

    blank = service.handle(
        ServiceRequest(
            "b",
            "retrieval_service",
            "search",
            payload={
                "query": "   ",
            },
        )
    )

    eq(
        blank.error.code,
        "INVALID_REQUEST",
        "blank query rejected",
    )

    missing = service.handle(
        ServiceRequest(
            "m",
            "retrieval_service",
            "remove_document",
            payload={
                "document_id": "missing",
            },
        )
    )

    eq(
        missing.error.code,
        "NOT_FOUND",
        "missing document removal maps to NOT_FOUND",
    )


def test_validation():
    worker = manager()

    expect_error(
        ValueError,
        lambda: worker.index_documents(
            documents(),
            mode="unknown",
        ),
        "invalid indexing mode rejected",
    )

    worker.document_store.replace_all(
        documents()
    )

    expect_error(
        RuntimeError,
        lambda: worker.rebuild(
            refit=False
        ),
        "unfitted IDF rebuild without refit rejected",
    )

    expect_error(
        TypeError,
        lambda: RetrievalService(
            worker
        ).handle(
            {}
        ),
        "non-ServiceRequest rejected",
    )


def main():
    try:
        test_document_store()
        test_index_build()
        test_search_ranking_and_dedup()
        test_filtering()
        test_transparent_boost()
        test_mmr()
        test_upsert_refit()
        test_remove_document()
        test_clear()
        test_persistence_round_trip()
        test_persistence_tokenizer_guard()
        test_persistence_corruption()
        test_service_flow()
        test_service_protocol_round_trip()
        test_service_state()
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
        "RETRIEVAL SERVICE TEST SUITE: PASS"
    )
    print(
        "Assertions passed:",
        ASSERTIONS,
    )
    print(
        "Files validated: 5/5"
    )
    print(
        "Document chunking + exact source offsets: VALIDATED"
    )
    print(
        "Full-corpus TF-IDF rebuild semantics: VALIDATED"
    )
    print(
        "Exact vector indexing/filtering: VALIDATED"
    )
    print(
        "Dedup/rerank/MMR pipeline: VALIDATED"
    )
    print(
        "Document upsert/removal + IDF refit: VALIDATED"
    )
    print(
        "Provenance-preserving search results: VALIDATED"
    )
    print(
        "Coherent retrieval state persistence: VALIDATED"
    )
    print(
        "Tokenizer-state compatibility guard: VALIDATED"
    )
    print(
        "Protocol service operations: VALIDATED"
    )
    print(
        "Third-party dependencies: 0"
    )


main()
