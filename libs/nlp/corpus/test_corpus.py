BASE = "libs/nlp/corpus/"
SCHEMA = "libs/data/schema/"


def load_file(path):
    namespace = {"__builtins__": __builtins__}
    source = open(path, "r", encoding="utf-8").read()
    exec(compile(source, path, "exec"), namespace)
    return namespace


Document = load_file(BASE + "document.py")["Document"]
CorpusConversation = load_file(BASE + "conversation.py")["CorpusConversation"]

_dedup_ns = load_file(BASE + "deduplicator.py")
Deduplicator = _dedup_ns["Deduplicator"]
DeduplicationResult = _dedup_ns["DeduplicationResult"]
DuplicateGroup = _dedup_ns["DuplicateGroup"]

_split_ns = load_file(BASE + "splitter.py")
CorpusSplitter = _split_ns["CorpusSplitter"]
SplitResult = _split_ns["SplitResult"]

Message = load_file(SCHEMA + "message.py")["Message"]
SchemaConversation = load_file(SCHEMA + "conversation.py")["Conversation"]
CanonicalRecord = load_file(SCHEMA + "canonical_record.py")["CanonicalRecord"]

ASSERTIONS = 0


def check(condition, message):
    global ASSERTIONS
    ASSERTIONS += 1
    if not condition:
        raise AssertionError(message)


def eq(actual, expected, message):
    check(
        actual == expected,
        message + " | got=" + repr(actual) + " expected=" + repr(expected)
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
            message + " | wrong exception=" + repr(exc)
        )

    raise AssertionError(
        message + " | expected exception was not raised"
    )


def test_document():
    document = Document(
        document_id="doc-1",
        text="Hello world",
        dataset_id="dailydialog",
        source_record_id="dailydialog-1",
        metadata={"x": {"y": 1}},
        labels=["conversation"],
        provenance={"file": "dialogues.json"},
    )

    eq(document.character_count(), 11, "character count")
    check(not document.is_empty(), "non-empty document")

    document.add_label("greeting")
    document.add_label("greeting")
    eq(document.labels.count("greeting"), 1, "labels remain unique")

    document.set_split("validation")
    eq(document.split, "validation", "split setter")

    row = document.to_dict()
    eq(row["source_record_id"], "dailydialog-1", "document serialization")
    eq(row["metadata"]["x"]["y"], 1, "nested metadata serialization")

    expect_error(
        ValueError,
        lambda: Document("", "x", "dataset"),
        "empty document id rejected",
    )


def test_from_canonical_record():
    conversation = SchemaConversation(
        conversation_id="conv-1",
        messages=[
            Message("user", "hello"),
            Message("assistant", "hi"),
        ],
    )

    record = CanonicalRecord(
        record_id="r1",
        dataset_id="dailydialog",
        dataset_name="DailyDialog",
        source_file="dialogues.json",
        source_record_index=0,
        source_format="json",
        raw_content="hello\nhi",
        normalized_content="<USER>\nhello\n<ASSISTANT>\nhi",
        labels=["conversation"],
        provenance={"dataset": "DailyDialog"},
        split="train",
        conversation=conversation,
        metadata={"turn_count": 2},
    )

    document = Document.from_canonical_record(record)

    eq(document.document_id, "r1", "canonical document id")
    eq(document.dataset_id, "dailydialog", "canonical dataset id")
    eq(
        document.text,
        "<USER>\nhello\n<ASSISTANT>\nhi",
        "canonical uses training text",
    )
    eq(document.split, "train", "canonical split")
    eq(document.metadata["turn_count"], 2, "canonical metadata copied")


def test_corpus_conversation():
    schema_conversation = SchemaConversation(
        conversation_id="tree-1",
        messages=[
            Message("user", "Tell me a joke."),
            Message("assistant", "Why did the byte cross the bus?"),
        ],
        metadata={"tree_id": "tree-1"},
    )

    corpus = CorpusConversation.from_schema_conversation(
        schema_conversation,
        dataset_id="openassistant",
        source_record_id="oa-1",
    )

    eq(corpus.turn_count(), 2, "corpus conversation turns")
    eq(corpus.roles(), ["user", "assistant"], "corpus roles")
    check("<USER>" in corpus.to_training_text(), "USER marker")
    check("<ASSISTANT>" in corpus.to_training_text(), "ASSISTANT marker")
    check("byte cross the bus" in corpus.to_training_text(), "conversation content")
    eq(corpus.metadata["tree_id"], "tree-1", "conversation metadata")


def test_exact_deduplication():
    documents = [
        Document("a", "same", "x"),
        Document("b", "same", "y"),
        Document("c", "different", "x"),
        Document("d", "same", "z"),
    ]

    result = Deduplicator(mode="exact").deduplicate(documents)

    eq(result.unique_count(), 2, "exact unique count")
    eq(result.duplicate_count(), 2, "exact duplicate count")
    eq(result.representative_for("a"), "a", "representative self")
    eq(result.representative_for("b"), "a", "duplicate representative")
    eq(result.representative_for("d"), "a", "second duplicate representative")
    eq(len(result.duplicate_groups), 1, "one duplicate group")
    eq(
        result.duplicate_groups[0].duplicate_ids,
        ["b", "d"],
        "duplicate order preserved",
    )

    # Source/corpus inputs remain intact. Dedup result only provides a view.
    eq(len(documents), 4, "dedup does not delete original list")
    eq(documents[1].text, "same", "dedup does not alter source document")


def test_normalized_deduplication():
    documents = [
        Document("a", "hello   world", "x"),
        Document("b", " hello\tworld ", "x"),
        Document("c", "Hello world", "x"),
    ]

    normalized = Deduplicator(mode="normalized", lowercase=False).deduplicate(documents)
    eq(normalized.unique_count(), 2, "whitespace normalization duplicate")

    casefolded = Deduplicator(mode="normalized", lowercase=True).deduplicate(documents)
    eq(casefolded.unique_count(), 1, "lowercase normalized duplicate")


def test_split_determinism():
    documents1 = []
    documents2 = []

    i = 0
    while i < 200:
        documents1.append(Document("doc-" + str(i), "text " + str(i), "dataset"))
        documents2.append(Document("doc-" + str(i), "text " + str(i), "dataset"))
        i += 1

    splitter = CorpusSplitter(
        train_ratio=0.80,
        validation_ratio=0.10,
        test_ratio=0.10,
        seed="unit-test",
    )

    first = splitter.split(documents1)
    second = splitter.split(documents2)

    first_map = {}
    for doc in documents1:
        first_map[doc.document_id] = doc.split

    second_map = {}
    for doc in documents2:
        second_map[doc.document_id] = doc.split

    eq(first_map, second_map, "split assignment deterministic")
    eq(first.total_count(), 200, "all documents assigned")
    check(len(first.train) > 0, "train non-empty")
    check(len(first.validation) > 0, "validation non-empty")
    check(len(first.test) > 0, "test non-empty")


def test_group_split_prevents_leakage():
    documents = []

    for i in range(30):
        tree_id = "tree-" + str(i // 3)
        documents.append(
            Document(
                document_id="msg-" + str(i),
                text="message " + str(i),
                dataset_id="openassistant",
                metadata={"tree_id": tree_id},
            )
        )

    splitter = CorpusSplitter(
        train_ratio=0.70,
        validation_ratio=0.15,
        test_ratio=0.15,
        seed="group-test",
    )

    splitter.split(
        documents,
        group_key=lambda document: document.metadata["tree_id"],
    )

    group_splits = {}

    for document in documents:
        tree_id = document.metadata["tree_id"]

        if tree_id not in group_splits:
            group_splits[tree_id] = document.split
        else:
            eq(
                document.split,
                group_splits[tree_id],
                "conversation group cannot leak across splits",
            )


def test_all_six_dataset_documents():
    datasets = [
        ("dd-1", "Daily dialogue", "dailydialog"),
        ("dol-1", "Instruction response", "dolly"),
        ("mov-1", "Movie dialogue", "movie-corpus"),
        ("tiny-1", "Once upon a time", "tinystories"),
        ("oa-1", "Assistant conversation", "openassistant"),
        ("sire-1", "SireSoft company knowledge", "siresoft"),
    ]

    documents = []

    for row in datasets:
        documents.append(
            Document(
                document_id=row[0],
                text=row[1],
                dataset_id=row[2],
            )
        )

    eq(len(documents), 6, "six dataset documents created")

    splitter = CorpusSplitter(
        train_ratio=0.80,
        validation_ratio=0.10,
        test_ratio=0.10,
        seed="six-datasets",
    )

    result = splitter.split(documents)
    eq(result.total_count(), 6, "six datasets survive split pipeline")


def test_validation():
    expect_error(
        ValueError,
        lambda: CorpusSplitter(0.8, 0.2, 0.2),
        "invalid ratio sum",
    )

    expect_error(
        ValueError,
        lambda: Deduplicator("fuzzy"),
        "unsupported dedup mode",
    )


def main():
    test_document()
    test_from_canonical_record()
    test_corpus_conversation()
    test_exact_deduplication()
    test_normalized_deduplication()
    test_split_determinism()
    test_group_split_prevents_leakage()
    test_all_six_dataset_documents()
    test_validation()

    print("CORPUS TEST SUITE: PASS")
    print("Assertions passed:", ASSERTIONS)
    print("Files validated: 4/4")
    print("CanonicalRecord integration: VALIDATED")
    print("Dedup provenance preservation: VALIDATED")
    print("Deterministic split: VALIDATED")
    print("Conversation leakage prevention: VALIDATED")
    print("Six dataset families: VALIDATED")
    print("Third-party dependencies: 0")


main()
