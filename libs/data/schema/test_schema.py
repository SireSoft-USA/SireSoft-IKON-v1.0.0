BASE = "libs/data/schema/"


def load_file(filename, extra=None):
    namespace = {"__builtins__": __builtins__}
    if extra is not None:
        for key in extra:
            namespace[key] = extra[key]
    path = BASE + filename
    source = open(path, "r", encoding="utf-8").read()
    exec(compile(source, path, "exec"), namespace)
    return namespace


_message_ns = load_file("message.py")
Message = _message_ns["Message"]

_conversation_ns = load_file("conversation.py")
Conversation = _conversation_ns["Conversation"]

_record_ns = load_file("canonical_record.py")
CanonicalRecord = _record_ns["CanonicalRecord"]

_validator_ns = load_file("validator.py")
ValidationIssue = _validator_ns["ValidationIssue"]
ValidationResult = _validator_ns["ValidationResult"]
SchemaValidator = _validator_ns["SchemaValidator"]

ASSERTIONS = 0


def check(condition, message):
    global ASSERTIONS
    ASSERTIONS += 1
    if not condition:
        raise AssertionError(message)


def check_equal(actual, expected, message):
    check(actual == expected, message + " | got=" + repr(actual) + " expected=" + repr(expected))


def expect_error(error_type, fn, message):
    global ASSERTIONS
    ASSERTIONS += 1
    try:
        fn()
    except error_type:
        return
    except Exception as exc:
        raise AssertionError(message + " | wrong exception=" + repr(exc))
    raise AssertionError(message + " | expected exception was not raised")


def build_record(record_id="r1", normalized_content="hello normalized"):
    user = Message("user", "hello", source_index=0)
    assistant = Message("assistant", "hi there", source_index=1)
    conversation = Conversation(
        conversation_id="conv-1",
        messages=[user, assistant],
        metadata={"topic": "greeting"},
        raw={"source": "dialogue"},
    )

    return CanonicalRecord(
        record_id=record_id,
        dataset_id="dailydialog",
        dataset_name="DailyDialog",
        source_file="dialogues.json",
        source_record_index=12,
        source_format="json",
        raw_content='{"dialogue":["hello","hi there"]}',
        normalized_content=normalized_content,
        original_fields={
            "dialogue": ["hello", "hi there"],
            "act": [1, 1],
            "emotion": [0, 0],
        },
        labels=["conversation", "daily"],
        language="en",
        document_type="conversation",
        source_type="dataset",
        provenance={"dataset": "DailyDialog"},
        checksum="abc123",
        preprocessing_history=[],
        split="train",
        conversation=conversation,
        metadata={"adapter": "dailydialog"},
    )


def test_message():
    message = Message(
        "user",
        "How are you?",
        name="speaker_1",
        metadata={"emotion": "neutral"},
        source_index=7,
        raw={"utterance": "How are you?"},
    )

    check_equal(message.role, "user", "message role")
    check_equal(message.content, "How are you?", "message content")
    check_equal(message.name, "speaker_1", "message name")
    check_equal(message.source_index, 7, "source index")
    check_equal(message.character_count(), 12, "character count")
    check_equal(message.is_empty(), False, "non-empty message")

    clone = message.clone()
    check_equal(clone.to_dict(), message.to_dict(), "message clone")
    clone.metadata["emotion"] = "happy"
    check_equal(message.metadata["emotion"], "neutral", "metadata copy isolation")

    check_equal(Message("assistant", "").is_empty(), True, "empty message")
    expect_error(ValueError, lambda: Message("alien", "hi"), "invalid role")
    expect_error(TypeError, lambda: Message("user", 123), "content type")


def test_conversation():
    c = Conversation(conversation_id="c1", title="Greeting")
    check_equal(c.message_count(), 0, "empty conversation")

    first = Message("user", "hello")
    second = Message("assistant", "hi")

    check_equal(c.add_message(first), 0, "first inserted index")
    check_equal(c.add_message(second), 1, "second inserted index")
    check_equal(len(c), 2, "conversation len")
    check_equal(c.roles(), ["user", "assistant"], "role order")
    check_equal(c.character_count(), 7, "conversation chars")
    check_equal(c.get_message(1).content, "hi", "get message")

    c.insert_message(1, Message("system", "context"))
    check_equal(c.roles(), ["user", "system", "assistant"], "insert order")
    removed = c.remove_message(1)
    check_equal(removed.role, "system", "remove message")
    check_equal(c.roles(), ["user", "assistant"], "roles restored")

    serialized = c.to_dict()
    check_equal(serialized["conversation_id"], "c1", "conversation serialization")
    check_equal(serialized["messages"][0]["content"], "hello", "message serialization")

    copy_list = c.messages()
    copy_list.append(Message("user", "external"))
    check_equal(c.message_count(), 2, "messages() returns isolated list")


def test_canonical_record():
    record = build_record()

    check_equal(record.record_id, "r1", "record id")
    check_equal(record.dataset_name, "DailyDialog", "dataset name")
    check_equal(record.source_record_index, 12, "source record index")
    check_equal(record.training_text(), "hello normalized", "normalized training text")
    check_equal(record.preserves_source(), True, "source preservation")

    record.add_label("greeting")
    record.add_label("greeting")
    check_equal(record.labels.count("greeting"), 1, "labels unique")

    record.add_preprocessing_step("normalize_whitespace", {"changed": False})
    check_equal(len(record.preprocessing_history), 1, "history append")
    check_equal(record.preprocessing_history[0]["name"], "normalize_whitespace", "history name")

    record.set_split("validation")
    check_equal(record.split, "validation", "set split")

    serialized = record.to_dict()
    check_equal(serialized["original_fields"]["act"], [1, 1], "original fields preserved")
    check_equal(serialized["conversation"]["messages"][1]["role"], "assistant", "conversation preserved")

    no_normalized = build_record("r2", normalized_content=None)
    text = no_normalized.training_text()
    check("<USER>" in text, "conversation fallback has user marker")
    check("<ASSISTANT>" in text, "conversation fallback has assistant marker")
    check("hello" in text and "hi there" in text, "conversation fallback content")

    raw_only = CanonicalRecord(
        record_id="raw-1",
        dataset_id="siresoft",
        dataset_name="SireSoft",
        source_file="siresoft.txt",
        source_record_index=0,
        source_format="txt",
        raw_content="Company knowledge",
    )
    check_equal(raw_only.training_text(), "Company knowledge", "raw fallback")

    expect_error(ValueError, lambda: record.set_split("production"), "invalid split")
    expect_error(
        ValueError,
        lambda: CanonicalRecord(
            record_id="",
            dataset_id="x",
            dataset_name="x",
            source_file="x",
            source_record_index=0,
            source_format="txt",
        ),
        "empty record id",
    )


def test_validator():
    validator = SchemaValidator()
    record = build_record()

    result = validator.validate_record(record)
    check_equal(result.is_valid(), True, "valid record")
    check_equal(result.error_count(), 0, "valid record errors")

    empty_message = Message("user", "")
    message_result = validator.validate_message(empty_message)
    check_equal(message_result.is_valid(), True, "empty message warning only")
    check_equal(message_result.warning_count(), 1, "empty message warning")

    empty_conversation = Conversation()
    conversation_result = validator.validate_conversation(empty_conversation)
    check_equal(conversation_result.is_valid(), True, "empty conversation warning only")
    check_equal(conversation_result.warning_count(), 1, "empty conversation warning")

    source_less = CanonicalRecord(
        record_id="source-less",
        dataset_id="x",
        dataset_name="X",
        source_file="x.json",
        source_record_index=0,
        source_format="json",
    )
    source_result = validator.validate_record(source_less)
    check_equal(source_result.is_valid(), True, "missing payload is warning")
    check(source_result.warning_count() >= 1, "missing payload warning exists")

    weird_format = CanonicalRecord(
        record_id="fmt",
        dataset_id="x",
        dataset_name="X",
        source_file="x.weird",
        source_record_index=0,
        source_format="weird",
        raw_content="data",
    )
    format_result = validator.validate_record(weird_format)
    check_equal(format_result.is_valid(), True, "unknown format warning only")
    check(format_result.warning_count() >= 1, "unknown format warning")

    duplicates = validator.validate_unique_record_ids([
        build_record("same"),
        build_record("same"),
        build_record("different"),
    ])
    check_equal(duplicates.is_valid(), False, "duplicate ids invalid")
    check_equal(duplicates.error_count(), 1, "one duplicate error")


def test_six_dataset_shapes():
    # DailyDialog
    daily = CanonicalRecord(
        "dd-1", "dailydialog", "DailyDialog", "dialogues.json", 0, "json",
        original_fields={"dialogue": ["hello", "hi"], "emotion": [0, 0]},
        conversation=Conversation(messages=[
            Message("user", "hello"),
            Message("assistant", "hi"),
        ]),
    )
    check_equal(daily.original_fields["emotion"], [0, 0], "DailyDialog metadata")

    # Dolly
    dolly = CanonicalRecord(
        "dol-1", "dolly", "Databricks Dolly 15K", "dolly.jsonl", 0, "jsonl",
        original_fields={
            "instruction": "Explain AI",
            "context": "",
            "response": "AI...",
            "category": "open_qa",
        },
        normalized_content="<USER>\nExplain AI\n<ASSISTANT>\nAI...",
    )
    check_equal(dolly.original_fields["category"], "open_qa", "Dolly metadata")

    # Cornell movie corpus
    movie = CanonicalRecord(
        "mov-1", "movie-corpus", "Cornell Movie Dialogs", "utterances.json", 3, "json",
        original_fields={"speaker": "u0", "movie_id": "m0", "utterance": "Hello"},
        raw_content="Hello",
    )
    check_equal(movie.original_fields["movie_id"], "m0", "movie metadata")

    # TinyStories
    tiny = CanonicalRecord(
        "tiny-1", "tinystories", "TinyStories", "TinyStories-train.txt", 1, "txt",
        raw_content="Once there was a cat.",
        document_type="story",
    )
    check_equal(tiny.training_text(), "Once there was a cat.", "TinyStories text")

    # OpenAssistant
    oasst = CanonicalRecord(
        "oa-1", "openassistant", "OpenAssistant OASST1", "oasst1-ready.jsonl", 5, "jsonl",
        original_fields={"message_id": "m1", "parent_id": None, "role": "prompter"},
        conversation=Conversation(messages=[Message("user", "Tell me a joke")]),
    )
    check_equal(oasst.original_fields["role"], "prompter", "OASST source role")

    # SireSoft
    sire = CanonicalRecord(
        "sire-1", "siresoft", "SireSoft", "siresoft.txt", 0, "txt",
        raw_content="SireSoft company information",
        source_type="company_knowledge",
        metadata={"rag_eligible": True},
    )
    check_equal(sire.metadata["rag_eligible"], True, "SireSoft RAG eligibility")

    validator = SchemaValidator()
    all_records = [daily, dolly, movie, tiny, oasst, sire]
    i = 0
    while i < len(all_records):
        result = validator.validate_record(all_records[i])
        check_equal(result.is_valid(), True, "dataset record validates")
        i += 1


def main():
    test_message()
    test_conversation()
    test_canonical_record()
    test_validator()
    test_six_dataset_shapes()

    print("SCHEMA TEST SUITE: PASS")
    print("Assertions passed:", ASSERTIONS)
    print("Files validated: 4/4")
    print("Six dataset shapes validated: 6/6")
    print("Third-party dependencies: 0")


main()
