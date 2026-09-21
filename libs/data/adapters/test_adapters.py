# SireLLM dataset adapter test suite.
# Uses only project source files and Python built-ins.

SCHEMA = "libs/data/schema/"
ADAPTERS = "libs/data/adapters/"


def load_file(path):
    namespace = {"__builtins__": __builtins__}
    source = open(path, "r", encoding="utf-8").read()
    exec(compile(source, path, "exec"), namespace)
    return namespace


Message = load_file(SCHEMA + "message.py")["Message"]
Conversation = load_file(SCHEMA + "conversation.py")["Conversation"]
CanonicalRecord = load_file(SCHEMA + "canonical_record.py")["CanonicalRecord"]
SchemaValidator = load_file(SCHEMA + "validator.py")["SchemaValidator"]

DailyDialogAdapter = load_file(ADAPTERS + "dailydialog_adapter.py")["DailyDialogAdapter"]
DollyAdapter = load_file(ADAPTERS + "dolly_adapter.py")["DollyAdapter"]
MovieCorpusAdapter = load_file(ADAPTERS + "movie_corpus_adapter.py")["MovieCorpusAdapter"]
SireSoftAdapter = load_file(ADAPTERS + "siresoft_adapter.py")["SireSoftAdapter"]
TinyStoriesAdapter = load_file(ADAPTERS + "tinystories_adapter.py")["TinyStoriesAdapter"]
OpenAssistantAdapter = load_file(ADAPTERS + "openassistant_adapter.py")["OpenAssistantAdapter"]

ASSERTIONS = 0


def check(condition, message):
    global ASSERTIONS
    ASSERTIONS += 1
    if not condition:
        raise AssertionError(message)


def eq(actual, expected, message):
    check(actual == expected, message + " | got=" + repr(actual) + " expected=" + repr(expected))


def validate(record):
    result = SchemaValidator().validate_record(record)
    check(result.is_valid(), "canonical record must pass schema validation")
    return result


def test_dailydialog():
    adapter = DailyDialogAdapter(CanonicalRecord, Conversation, Message)

    source = {
        "dialogue": ["Hello!", "Hi, how are you?", "Good."],
        "act": [1, 2, 1],
        "emotion": [0, 0, 4],
        "custom_source_field": {"must": "survive"},
    }

    record = adapter.adapt_record(source, 4)

    eq(record.dataset_id, "dailydialog", "DailyDialog dataset id")
    eq(record.conversation.message_count(), 3, "DailyDialog message count")
    eq(record.conversation.roles(), ["user", "assistant", "user"], "DailyDialog alternating roles")
    eq(record.original_fields["custom_source_field"]["must"], "survive", "DailyDialog unknown field preserved")
    eq(record.original_fields["emotion"], [0, 0, 4], "DailyDialog emotion preserved")
    check("<USER>" in record.normalized_content, "DailyDialog normalized user marker")
    validate(record)


def test_dolly():
    adapter = DollyAdapter(CanonicalRecord, Conversation, Message)

    source = {
        "instruction": "Explain recursion.",
        "context": "Use a simple explanation.",
        "response": "Recursion is when a process refers to itself.",
        "category": "open_qa",
        "extra": 123,
    }

    record = adapter.adapt_record(source, 9)

    eq(record.dataset_id, "dolly", "Dolly dataset id")
    eq(record.conversation.message_count(), 2, "Dolly two-message conversation")
    check("Use a simple explanation." in record.conversation.get_message(0).content, "Dolly context retained")
    eq(record.original_fields["extra"], 123, "Dolly extra source field preserved")
    check("open_qa" in record.labels, "Dolly category label")
    validate(record)


def test_movie_corpus():
    adapter = MovieCorpusAdapter(CanonicalRecord, Conversation, Message)

    source = {
        "conversation_id": "L1-L2",
        "movie_id": "m0",
        "utterances": [
            {"speaker": "u0", "text": "Hello there.", "line_id": "L1"},
            {"speaker": "u1", "text": "General Kenobi.", "line_id": "L2"},
        ],
        "unmapped_field": "preserve-me",
    }

    record = adapter.adapt_conversation(source, 2)

    eq(record.dataset_id, "movie-corpus", "movie dataset id")
    eq(record.conversation.get_message(0).name, "u0", "movie speaker preserved")
    eq(record.original_fields["unmapped_field"], "preserve-me", "movie unknown field preserved")
    eq(record.conversation.message_count(), 2, "movie message count")
    validate(record)

    utterance = adapter.adapt_utterance(
        {"speaker": "u5", "text": "One line.", "movie_id": "m5"},
        15,
    )
    eq(utterance.raw_content, "One line.", "movie utterance raw text")
    eq(utterance.metadata["speaker"], "u5", "movie utterance speaker")
    validate(utterance)


def test_siresoft():
    adapter = SireSoftAdapter(CanonicalRecord)

    text = "SireSoft\n\nServices and company information.\n"
    record = adapter.adapt_document(
        text,
        0,
        source_metadata={"url": "https://www.siresoft.net/", "captured_at": "source"},
    )

    eq(record.raw_content, text, "SireSoft source remains exact")
    eq(record.original_fields["text"], text, "SireSoft original field exact")
    eq(record.metadata["rag_eligible"], True, "SireSoft marked RAG eligible")
    eq(record.metadata["authoritative_company_source"], True, "SireSoft authoritative source marker")
    check("rag_source" in record.labels, "SireSoft RAG label")
    validate(record)


def test_tinystories():
    adapter = TinyStoriesAdapter(CanonicalRecord)

    story = "Once there was a small robot.\nIt wanted to learn."
    record = adapter.adapt_story(story, 18, metadata={"source_split": "train"})

    eq(record.raw_content, story, "TinyStories raw exact")
    eq(record.normalized_content, story, "TinyStories training text exact")
    eq(record.original_fields["story"], story, "TinyStories source preserved")
    eq(record.document_type, "story", "TinyStories document type")
    validate(record)


def test_openassistant():
    adapter = OpenAssistantAdapter(CanonicalRecord, Conversation, Message)

    first = {
        "message_id": "m1",
        "parent_id": None,
        "message_tree_id": "tree-1",
        "role": "prompter",
        "text": "Tell me a joke.",
        "lang": "en",
        "quality": {"value": 0.9},
    }

    message_record = adapter.adapt_message(first, 0)

    eq(message_record.conversation.get_message(0).role, "user", "OASST prompter maps to user")
    eq(message_record.original_fields["quality"]["value"], 0.9, "OASST extra metadata preserved")
    validate(message_record)

    second = {
        "message_id": "m2",
        "parent_id": "m1",
        "message_tree_id": "tree-1",
        "role": "assistant",
        "text": "Why did the byte cross the bus? To get to the other side.",
        "lang": "en",
    }

    conversation_record = adapter.adapt_conversation([first, second], 0)

    eq(conversation_record.conversation.message_count(), 2, "OASST conversation count")
    eq(conversation_record.conversation.roles(), ["user", "assistant"], "OASST role mapping")
    eq(conversation_record.original_fields["messages"][0]["message_id"], "m1", "OASST source record preserved")
    check("<ASSISTANT>" in conversation_record.normalized_content, "OASST assistant marker")
    validate(conversation_record)


def test_no_source_mutation():
    dolly_source = {
        "instruction": "A",
        "context": "B",
        "response": "C",
        "category": "x",
        "nested": {"value": [1, 2]},
    }

    adapter = DollyAdapter(CanonicalRecord, Conversation, Message)
    record = adapter.adapt_record(dolly_source, 0)

    record.original_fields["nested"]["value"].append(3)
    eq(dolly_source["nested"]["value"], [1, 2], "adapter deep copy prevents source mutation")


def main():
    test_dailydialog()
    test_dolly()
    test_movie_corpus()
    test_siresoft()
    test_tinystories()
    test_openassistant()
    test_no_source_mutation()

    print("ADAPTERS TEST SUITE: PASS")
    print("Assertions passed:", ASSERTIONS)
    print("Adapter files validated: 6/6")
    print("Dataset families validated: 6/6")
    print("Schema dependency validated: YES")
    print("Third-party dependencies: 0")


main()
