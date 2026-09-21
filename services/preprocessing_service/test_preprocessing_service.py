import os

SERIAL_BASE = "libs/core/serialization/"
PARSER_BASE = "libs/data/parsers/"
SCHEMA_BASE = "libs/data/schema/"
ADAPTER_BASE = "libs/data/adapters/"
STREAM_BASE = "libs/data/streaming/"
NORM_BASE = "libs/nlp/normalization/"
CORPUS_BASE = "libs/nlp/corpus/"
PROTOCOL_BASE = "libs/protocol/"
PRE_BASE = "services/preprocessing_service/"

namespace = {
    "__builtins__": __builtins__,
}

for filename in [
    "binary_writer.py",
    "binary_reader.py",
    "checksum.py",
]:
    path = SERIAL_BASE + filename
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
    "json_parser.py",
    "jsonl_parser.py",
    "text_parser.py",
]:
    path = PARSER_BASE + filename
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
    "message.py",
    "conversation.py",
    "canonical_record.py",
    "validator.py",
]:
    path = SCHEMA_BASE + filename
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
    "dailydialog_adapter.py",
    "dolly_adapter.py",
    "movie_corpus_adapter.py",
    "siresoft_adapter.py",
    "tinystories_adapter.py",
    "openassistant_adapter.py",
]:
    path = ADAPTER_BASE + filename
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

path = STREAM_BASE + "writer.py"
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
    "whitespace.py",
    "punctuation.py",
    "unicode_rules.py",
    "normalizer.py",
]:
    path = NORM_BASE + filename
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

path = CORPUS_BASE + "document.py"
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
    "error.py",
    "message.py",
    "request.py",
    "response.py",
    "validator.py",
    "codec.py",
]:
    path = PROTOCOL_BASE + filename
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
    "dataset_loader.py",
    "canonical_normalizer.py",
    "canonical_writer.py",
    "pipeline.py",
    "service.py",
]:
    path = PRE_BASE + filename
    source = open(
        path,
        "r",
        encoding="utf-8",
    ).read()

    if "import " in source:
        raise AssertionError(
            "preprocessing implementation contains forbidden import: "
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

ROOT = (
    "services/preprocessing_service/"
    "_test_raw"
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


def write_text(path, text):
    parent = os.path.dirname(
        path
    )

    if parent != "":
        os.makedirs(
            parent,
            exist_ok=True,
        )

    handle = open(
        path,
        "w",
        encoding="utf-8",
        newline="",
    )

    try:
        handle.write(text)
    finally:
        handle.close()


def cleanup():
    if not os.path.isdir(
        ROOT
    ):
        return

    for current, dirs, names in os.walk(
        ROOT,
        topdown=False,
    ):
        for name in names:
            os.remove(
                os.path.join(
                    current,
                    name,
                )
            )

        for name in dirs:
            os.rmdir(
                os.path.join(
                    current,
                    name,
                )
            )

    os.rmdir(ROOT)


def prepare_sources():
    cleanup()

    write_text(
        ROOT + "/dailydialog/dialogues.json",
        (
            '[{"dialogue":["Hello  there","Hi!"],'
            '"act":[1,2],"emotion":[0,1]}]'
        ),
    )

    write_text(
        ROOT + "/dailydialog/ontology.json",
        '{"acts":{"1":"inform"},"emotions":{"0":"neutral"}}',
    )

    write_text(
        ROOT + "/dolly/data.jsonl",
        (
            '{"instruction":"Explain software.",'
            '"context":"Short context.",'
            '"response":"Software is built code.",'
            '"category":"open_qa"}\n'
        ),
    )

    write_text(
        ROOT + "/movie/utterances.json",
        (
            '[{"id":"L1","text":"Hello","speaker":"A"},'
            '{"id":"L2","text":"Hi there","speaker":"B"}]'
        ),
    )

    write_text(
        ROOT + "/movie/conversations.json",
        (
            '[{"id":"C1","line_ids":["L1","L2"],'
            '"movie_id":"M1"}]'
        ),
    )

    write_text(
        ROOT + "/movie/corpus.json",
        '{"name":"Cornell","version":1}',
    )

    write_text(
        ROOT + "/movie/index.json",
        '{"L1":0,"L2":1}',
    )

    write_text(
        ROOT + "/movie/speakers.json",
        '{"A":{"name":"Alice"},"B":{"name":"Bob"}}',
    )

    write_text(
        ROOT + "/siresoft/siresoft.txt",
        (
            "SireSoft  builds “professional” software.\n"
            "It serves clients."
        ),
    )

    write_text(
        ROOT + "/tinystories/stories.txt",
        (
            "Story one."
            "<|endoftext|>"
            "Story two."
            "<|endoftext|>"
        ),
    )

    write_text(
        ROOT + "/openassistant/oasst.jsonl",
        (
            '{"message_id":"m1","message_tree_id":"t1",'
            '"parent_id":null,"role":"prompter","text":"Hello","lang":"en"}\n'
            '{"message_id":"m2","message_tree_id":"t1",'
            '"parent_id":"m1","role":"assistant","text":"Hi","lang":"en"}\n'
        ),
    )


def source_map(dataset_id):
    maps = {
        "dailydialog": {
            "dialogues": ROOT + "/dailydialog/dialogues.json",
            "ontology": ROOT + "/dailydialog/ontology.json",
        },
        "dolly": {
            "instructions": ROOT + "/dolly/data.jsonl",
        },
        "movie-corpus": {
            "conversations": ROOT + "/movie/conversations.json",
            "corpus": ROOT + "/movie/corpus.json",
            "index": ROOT + "/movie/index.json",
            "speakers": ROOT + "/movie/speakers.json",
            "utterances": ROOT + "/movie/utterances.json",
        },
        "siresoft": {
            "knowledge": ROOT + "/siresoft/siresoft.txt",
        },
        "tinystories": {
            "stories": ROOT + "/tinystories/stories.txt",
        },
        "openassistant": {
            "messages": ROOT + "/openassistant/oasst.jsonl",
        },
    }

    return maps[
        dataset_id
    ]


def pipeline():
    return build_default_preprocessing_pipeline()


def test_all_six_load():
    worker = pipeline()

    expected = {
        "dailydialog": 2,
        "dolly": 1,
        "movie-corpus": 6,
        "siresoft": 1,
        "tinystories": 2,
        "openassistant": 1,
    }

    for dataset_id in expected:
        result = worker.process(
            dataset_id,
            sources=source_map(
                dataset_id
            ),
            strict=True,
        )

        eq(
            len(result.records),
            expected[dataset_id],
            "canonical count " + dataset_id,
        )

        check(
            result.valid(),
            "schema valid " + dataset_id,
        )


def test_source_preservation():
    result = pipeline().process(
        "siresoft",
        sources=source_map(
            "siresoft"
        ),
        strict=True,
    )

    record = result.records[0]

    eq(
        record.raw_content,
        (
            "SireSoft  builds “professional” software.\n"
            "It serves clients."
        ),
        "SireSoft exact raw text preserved",
    )

    eq(
        record.normalized_content,
        (
            'SireSoft builds "professional" software.\n'
            "It serves clients."
        ),
        "model-facing normalization applied",
    )

    check(
        len(
            record.preprocessing_history
        ) >= 1,
        "normalization history recorded",
    )


def test_daily_ontology_preserved():
    result = pipeline().process(
        "dailydialog",
        sources=source_map(
            "dailydialog"
        ),
    )

    ontology = result.records[-1]

    eq(
        ontology.record_id,
        "dailydialog-ontology",
        "ontology auxiliary record created",
    )

    eq(
        ontology.original_fields[
            "root"
        ]["acts"]["1"],
        "inform",
        "ontology payload preserved",
    )

    eq(
        ontology.metadata[
            "training_eligible"
        ],
        False,
        "ontology excluded from model documents",
    )


def test_movie_reference_resolution():
    result = pipeline().process(
        "movie-corpus",
        sources=source_map(
            "movie-corpus"
        ),
        strict=True,
    )

    conversation = None

    for record in result.records:
        if record.record_id == "movie-0":
            conversation = record
            break

    check(
        conversation is not None,
        "resolved movie conversation exists",
    )

    messages = conversation.conversation.messages()

    eq(
        [
            message.content
            for message in messages
        ],
        [
            "Hello",
            "Hi there",
        ],
        "movie line IDs resolved to utterance text",
    )

    check(
        "_source_conversation"
        in conversation.original_fields,
        "original movie conversation retained",
    )


def test_tinystories_explicit_boundaries():
    result = pipeline().process(
        "tinystories",
        sources=source_map(
            "tinystories"
        ),
        strict=True,
    )

    eq(
        [
            record.raw_content
            for record in result.records
        ],
        [
            "Story one.",
            "Story two.",
        ],
        "TinyStories explicit delimiter split",
    )

    eq(
        result.records[0]
        .original_fields[
            "separator_after"
        ],
        "<|endoftext|>",
        "TinyStories delimiter preserved",
    )


def test_openassistant_grouping():
    result = pipeline().process(
        "openassistant",
        sources=source_map(
            "openassistant"
        ),
        strict=True,
    )

    eq(
        len(result.records),
        1,
        "OASST tree grouped into one conversation",
    )

    record = result.records[0]

    eq(
        len(
            record.original_fields[
                "messages"
            ]
        ),
        2,
        "all OASST source messages preserved",
    )

    eq(
        [
            message.role
            for message
            in record.conversation.messages()
        ],
        [
            "user",
            "assistant",
        ],
        "OASST roles mapped",
    )


def test_documents_exclude_auxiliary():
    result = pipeline().process(
        "movie-corpus",
        sources=source_map(
            "movie-corpus"
        ),
        strict=True,
    )

    eq(
        len(result.documents),
        3,
        "only utterance/conversation records become corpus documents",
    )

    ids = [
        document.document_id
        for document in result.documents
    ]

    check(
        "movie-aux-corpus"
        not in ids,
        "auxiliary records excluded from training corpus",
    )


def test_canonical_jsonl_export():
    output_path = (
        ROOT
        + "/output/siresoft.canonical.jsonl"
    )

    os.makedirs(
        os.path.dirname(
            output_path
        ),
        exist_ok=True,
    )

    result = pipeline().process(
        "siresoft",
        sources=source_map(
            "siresoft"
        ),
        strict=True,
        output_path=output_path,
    )

    eq(
        result.output_info[
            "record_count"
        ],
        1,
        "canonical export record count",
    )

    check(
        result.output_info[
            "bytes_written"
        ] > 0,
        "canonical export wrote bytes",
    )

    rows = list(
        JSONLParser(
            JSONParser()
        ).iter_file(
            output_path
        )
    )

    eq(
        rows[0]["record_id"],
        "siresoft-0",
        "export parses with handwritten JSONL parser",
    )

    eq(
        rows[0]["raw_content"],
        (
            "SireSoft  builds “professional” software.\n"
            "It serves clients."
        ),
        "export preserves exact raw content",
    )


def test_normalization_can_be_disabled():
    result = pipeline().process(
        "siresoft",
        sources=source_map(
            "siresoft"
        ),
        normalize=False,
        strict=True,
    )

    record = result.records[0]

    eq(
        record.normalized_content,
        record.raw_content,
        "disabled normalization leaves adapter content unchanged",
    )

    eq(
        record.preprocessing_history[
            -1
        ]["details"]["reason"],
        "disabled_by_pipeline",
        "disabled normalization recorded",
    )


def test_service_preview_and_preprocess():
    service = PreprocessingService(
        pipeline()
    )

    preview = service.handle(
        ServiceRequest(
            "p1",
            "preprocessing_service",
            "preview",
            payload={
                "dataset_id": "dolly",
                "sources": source_map(
                    "dolly"
                ),
            },
        )
    )

    eq(
        preview.success,
        True,
        "preview service succeeds",
    )

    eq(
        preview.data[
            "summary"
        ]["record_count"],
        1,
        "preview summary",
    )

    output_path = (
        ROOT
        + "/output/dolly.canonical.jsonl"
    )

    os.makedirs(
        os.path.dirname(
            output_path
        ),
        exist_ok=True,
    )

    processed = service.handle(
        ServiceRequest(
            "p2",
            "preprocessing_service",
            "preprocess",
            payload={
                "dataset_id": "dolly",
                "sources": source_map(
                    "dolly"
                ),
                "output_path": output_path,
                "strict": True,
            },
        )
    )

    eq(
        processed.success,
        True,
        "preprocess service succeeds",
    )

    eq(
        processed.data[
            "summary"
        ]["output"][
            "record_count"
        ],
        1,
        "preprocess output summary",
    )


def test_protocol_round_trip():
    service = PreprocessingService(
        pipeline()
    )

    codec = ProtocolCodec()

    request = ServiceRequest(
        "protocol-pre",
        "preprocessing_service",
        "preview",
        payload={
            "dataset_id": "openassistant",
            "sources": source_map(
                "openassistant"
            ),
        },
        trace_id="trace-pre",
    )

    restored_request = codec.decode_request(
        codec.encode_request(
            request
        )
    )

    response = service.handle(
        restored_request
    )

    restored_response = codec.decode_response(
        codec.encode_response(
            response
        )
    )

    eq(
        restored_response.success,
        True,
        "preprocessing works through binary protocol",
    )

    eq(
        restored_response.trace_id,
        "trace-pre",
        "trace preserved through preprocessing service",
    )

    eq(
        restored_response.data[
            "summary"
        ]["dataset_id"],
        "openassistant",
        "protocol response dataset",
    )


def test_supported_datasets():
    service = PreprocessingService(
        pipeline()
    )

    response = service.handle(
        ServiceRequest(
            "s",
            "preprocessing_service",
            "supported_datasets",
        )
    )

    eq(
        response.data["count"],
        6,
        "service exposes six datasets",
    )

    eq(
        response.data["datasets"][0],
        "dailydialog",
        "supported order stable",
    )


def test_errors():
    service = PreprocessingService(
        pipeline()
    )

    unsupported = service.handle(
        ServiceRequest(
            "e1",
            "preprocessing_service",
            "preview",
            payload={
                "dataset_id": "unknown",
            },
        )
    )

    eq(
        unsupported.success,
        False,
        "unknown dataset fails",
    )

    eq(
        unsupported.error.code,
        "INVALID_REQUEST",
        "unknown dataset error code",
    )

    wrong = service.handle(
        ServiceRequest(
            "e2",
            "rag_service",
            "preview",
        )
    )

    eq(
        wrong.error.code,
        "INVALID_REQUEST",
        "wrong service rejected",
    )


def test_validation():
    worker = pipeline()

    expect_error(
        ValueError,
        lambda: worker.loader.load(
            "unknown"
        ),
        "unknown loader dataset rejected",
    )

    expect_error(
        TypeError,
        lambda: PreprocessingService(
            worker
        ).handle(
            {}
        ),
        "non-ServiceRequest rejected",
    )

    expect_error(
        ValueError,
        lambda: CanonicalJSONLWriter().write(
            [],
            "",
        ),
        "empty output path rejected",
    )


def main():
    prepare_sources()

    try:
        test_all_six_load()
        test_source_preservation()
        test_daily_ontology_preserved()
        test_movie_reference_resolution()
        test_tinystories_explicit_boundaries()
        test_openassistant_grouping()
        test_documents_exclude_auxiliary()
        test_canonical_jsonl_export()
        test_normalization_can_be_disabled()
        test_service_preview_and_preprocess()
        test_protocol_round_trip()
        test_supported_datasets()
        test_errors()
        test_validation()

    finally:
        cleanup()

    print(
        "PREPROCESSING SERVICE TEST SUITE: PASS"
    )
    print(
        "Assertions passed:",
        ASSERTIONS,
    )
    print(
        "Files validated: 5/5"
    )
    print(
        "Six dataset loaders/adapters: VALIDATED"
    )
    print(
        "Raw source preservation: VALIDATED"
    )
    print(
        "Canonical normalization/history: VALIDATED"
    )
    print(
        "Schema validation + unique IDs: VALIDATED"
    )
    print(
        "Cornell reference resolution: VALIDATED"
    )
    print(
        "OASST conversation grouping: VALIDATED"
    )
    print(
        "Canonical JSONL export: VALIDATED"
    )
    print(
        "Corpus Document bridge: VALIDATED"
    )
    print(
        "Protocol service operations: VALIDATED"
    )
    print(
        "Third-party dependencies: 0"
    )


main()
