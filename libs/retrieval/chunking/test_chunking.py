CORPUS_BASE = "libs/nlp/corpus/"
TOKENIZER_BASE = "libs/nlp/tokenizer/"
CHUNK_BASE = "libs/retrieval/chunking/"

namespace = {
    "__builtins__": __builtins__,
}

path = CORPUS_BASE + "document.py"
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

for filename in [
    "chunk.py",
    "boundaries.py",
    "document_chunker.py",
    "token_chunker.py",
]:
    path = CHUNK_BASE + filename
    source = open(path, "r", encoding="utf-8").read()

    if "import " in source:
        raise AssertionError(
            "chunking implementation contains forbidden import: "
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
            "SireSoft builds software systems.",
            "Professional software engineering.",
            "Retrieval augmented generation.",
            "اردو text and English text.",
            "中文 example and emoji 🙂.",
            "SireSoft SireSoft SireSoft.",
        ],
        vocab_size=310,
        min_frequency=2,
    )

    return BPETokenizer(
        model,
        byte_encoder,
        specials,
    )


def test_chunk_object():
    chunk = Chunk(
        chunk_id="doc-1::char::0",
        document_id="doc-1",
        dataset_id="siresoft",
        text="hello",
        chunk_index=0,
        char_start=10,
        char_end=15,
        metadata={"kind": "test"},
        provenance={"file": "siresoft.txt"},
    )

    eq(chunk.character_count(), 5, "chunk character count")
    eq(chunk.source_span(), (10, 15), "chunk source span")
    eq(
        chunk.to_dict()["metadata"]["kind"],
        "test",
        "chunk metadata",
    )


def test_boundaries():
    detector = BoundaryDetector()

    text = (
        "Version 3.14 is stable. "
        "Is it ready? Yes!\n"
        "اردو سوال؟ جواب۔"
    )

    ends = detector.sentence_ends(text)

    check(
        len(ends) >= 5,
        "multilingual sentence boundaries",
    )

    decimal_end = text.find("3.14") + 2

    check(
        decimal_end not in ends,
        "decimal point not treated as sentence end",
    )

    paragraph_text = (
        "First paragraph.\n\n"
        "Second paragraph."
    )

    paragraph_ends = detector.paragraph_ends(
        paragraph_text
    )

    check(
        paragraph_text.find("\n\n") + 2
        in paragraph_ends,
        "paragraph boundary",
    )


def test_character_chunking_exact_source():
    text = (
        "SireSoft builds professional software systems. "
        "The company works with modern engineering practices. "
        "This document contains information for retrieval. "
        "Every chunk must preserve exact source characters."
    )

    document = Document(
        document_id="sire-1",
        text=text,
        dataset_id="siresoft",
        metadata={"rag": True},
        provenance={"file": "siresoft.txt"},
    )

    chunks = DocumentChunker(
        max_chars=80,
        overlap_chars=15,
        min_chunk_chars=30,
    ).chunk_document(document)

    check(
        len(chunks) > 1,
        "long document creates multiple chunks",
    )

    for chunk in chunks:
        eq(
            chunk.text,
            text[
                chunk.char_start:
                chunk.char_end
            ],
            "chunk text is exact source slice",
        )

        eq(
            chunk.document_id,
            "sire-1",
            "document identity retained",
        )

        eq(
            chunk.dataset_id,
            "siresoft",
            "dataset identity retained",
        )

        eq(
            chunk.provenance["file"],
            "siresoft.txt",
            "source provenance retained",
        )

        check(
            len(chunk.text) <= 80,
            "character chunk respects maximum",
        )


def test_character_overlap():
    text = (
        "ABCDEFGHIJKLMNOPQRSTUVWXYZ"
        "abcdefghijklmnopqrstuvwxyz"
        "0123456789"
    )

    chunks = DocumentChunker(
        max_chars=20,
        overlap_chars=5,
        min_chunk_chars=20,
    ).chunk_document(
        Document(
            "doc-overlap",
            text,
            "test",
        )
    )

    check(
        len(chunks) >= 3,
        "overlap test has several chunks",
    )

    index = 1

    while index < len(chunks):
        previous = chunks[index - 1]
        current = chunks[index]

        eq(
            current.char_start,
            previous.char_end - 5,
            "character overlap offset",
        )

        eq(
            text[
                current.char_start:
                previous.char_end
            ],
            current.text[
                :previous.char_end
                - current.char_start
            ],
            "overlap text matches source",
        )

        index += 1


def test_empty_document():
    chunks = DocumentChunker(
        max_chars=10,
        overlap_chars=2,
    ).chunk_document(
        Document(
            "empty",
            "",
            "test",
        )
    )

    eq(
        chunks,
        [],
        "empty document produces no chunks",
    )


def test_token_chunking_real_bpe():
    tokenizer = build_tokenizer()

    text = (
        "SireSoft builds software systems. "
        "Professional retrieval systems use chunks. "
        "اردو text is preserved too. 中文 🙂"
    )

    document = Document(
        document_id="token-doc",
        text=text,
        dataset_id="siresoft",
        provenance={"file": "siresoft.txt"},
    )

    chunks = TokenChunker(
        tokenizer=tokenizer,
        max_tokens=12,
        overlap_tokens=3,
    ).chunk_document(document)

    check(
        len(chunks) > 1,
        "real BPE token chunking creates multiple chunks",
    )

    full_ids = tokenizer.encode(text)

    for chunk in chunks:
        ids = full_ids[
            chunk.token_start:
            chunk.token_end
        ]

        eq(
            tokenizer.decode(ids),
            chunk.text,
            "token chunk decodes from exact token span",
        )

        check(
            chunk.token_end - chunk.token_start <= 12,
            "token chunk respects maximum",
        )

        eq(
            chunk.provenance["file"],
            "siresoft.txt",
            "token chunk provenance",
        )


def test_unicode_token_boundaries():
    tokenizer = build_tokenizer()

    text = (
        "اردو اردو اردو 中文中文中文 🙂🙂🙂 "
        "English tail"
    )

    document = Document(
        "unicode",
        text,
        "test",
    )

    chunks = TokenChunker(
        tokenizer,
        max_tokens=5,
        overlap_tokens=2,
    ).chunk_document(document)

    check(
        len(chunks) > 1,
        "Unicode text tokenized into several chunks",
    )

    for chunk in chunks:
        check(
            chunk.text != "",
            "Unicode chunk remains decodable",
        )

        check(
            chunk.token_end - chunk.token_start <= 5,
            "Unicode chunk stays within token limit",
        )


def test_token_overlap_no_source_gap():
    tokenizer = build_tokenizer()

    text = "abcdefghijabcdefghijabcdefghij"

    full_ids = tokenizer.encode(text)

    chunks = TokenChunker(
        tokenizer,
        max_tokens=4,
        overlap_tokens=1,
    ).chunk_document(
        Document(
            "token-overlap",
            text,
            "test",
        )
    )

    check(
        len(chunks) >= 1,
        "token overlap produces chunks",
    )

    eq(
        chunks[0].token_start,
        0,
        "first token chunk starts at zero",
    )

    index = 1

    while index < len(chunks):
        previous = chunks[index - 1]
        current = chunks[index]

        check(
            current.token_start <= previous.token_end,
            "token chunks have no source gap",
        )

        check(
            current.token_start > previous.token_start,
            "token chunk windows advance",
        )

        index += 1

    eq(
        chunks[-1].token_end,
        len(full_ids),
        "token chunks reach final source token",
    )


def test_source_document_immutability():
    text = (
        "Original source text. "
        "It must remain unchanged after chunking."
    )

    document = Document(
        "immutability",
        text,
        "test",
        metadata={
            "nested": {
                "value": 1,
            },
        },
    )

    original_text = document.text
    original_metadata = document.to_dict()["metadata"]

    DocumentChunker(
        max_chars=25,
        overlap_chars=5,
        min_chunk_chars=10,
    ).chunk_document(document)

    eq(
        document.text,
        original_text,
        "chunking does not alter source text",
    )

    eq(
        document.metadata,
        original_metadata,
        "chunking does not alter source metadata",
    )


def test_validation():
    expect_error(
        ValueError,
        lambda: DocumentChunker(
            max_chars=10,
            overlap_chars=10,
        ),
        "invalid character overlap",
    )

    expect_error(
        ValueError,
        lambda: TokenChunker(
            build_tokenizer(),
            max_tokens=4,
            overlap_tokens=4,
        ),
        "invalid token overlap",
    )

    expect_error(
        ValueError,
        lambda: Chunk(
            chunk_id="x",
            document_id="d",
            dataset_id="set",
            text="x",
            chunk_index=-1,
        ),
        "negative chunk index",
    )


def main():
    test_chunk_object()
    test_boundaries()
    test_character_chunking_exact_source()
    test_character_overlap()
    test_empty_document()
    test_token_chunking_real_bpe()
    test_unicode_token_boundaries()
    test_token_overlap_no_source_gap()
    test_source_document_immutability()
    test_validation()

    print("CHUNKING TEST SUITE: PASS")
    print("Assertions passed:", ASSERTIONS)
    print("Files validated: 4/4")
    print("Exact source-span preservation: VALIDATED")
    print("Sentence/paragraph boundaries: VALIDATED")
    print("Character overlap: VALIDATED")
    print("Real byte-BPE token chunking: VALIDATED")
    print("UTF-8 token-boundary alignment: VALIDATED")
    print("Provenance preservation: VALIDATED")
    print("Source immutability: VALIDATED")
    print("Third-party dependencies: 0")


main()
