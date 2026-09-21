import os
import shutil

SERIAL_BASE = "libs/core/serialization/"
PARSER_BASE = "libs/data/parsers/"
SCHEMA_BASE = "libs/data/schema/"
ADAPTER_BASE = "libs/data/adapters/"
STREAM_BASE = "libs/data/streaming/"
NORM_BASE = "libs/nlp/normalization/"
CORPUS_BASE = "libs/nlp/corpus/"
PROTOCOL_BASE = "libs/protocol/"
PRE_BASE = "services/preprocessing_service/"
CONFIG_BASE = "configs/preprocessing/"

namespace = {
    "__builtins__": __builtins__,
}

groups = [
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
            "jsonl_parser.py",
            "text_parser.py",
        ],
    ),
    (
        SCHEMA_BASE,
        [
            "message.py",
            "conversation.py",
            "canonical_record.py",
            "validator.py",
        ],
    ),
    (
        ADAPTER_BASE,
        [
            "dailydialog_adapter.py",
            "dolly_adapter.py",
            "movie_corpus_adapter.py",
            "siresoft_adapter.py",
            "tinystories_adapter.py",
            "openassistant_adapter.py",
        ],
    ),
    (
        STREAM_BASE,
        [
            "writer.py",
        ],
    ),
    (
        NORM_BASE,
        [
            "whitespace.py",
            "punctuation.py",
            "unicode_rules.py",
            "normalizer.py",
        ],
    ),
    (
        CORPUS_BASE,
        [
            "document.py",
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
        PRE_BASE,
        [
            "dataset_loader.py",
            "canonical_normalizer.py",
            "canonical_writer.py",
            "pipeline.py",
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
    "dataset.py",
    "config.py",
    "defaults.py",
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
            "preprocessing config implementation contains forbidden import: "
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
ROOT = "configs/preprocessing/_test_data"


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


def write_text(path, text):
    parent = os.path.dirname(path)
    if parent != "":
        os.makedirs(
            parent,
            exist_ok=True,
        )

    with open(
        path,
        "w",
        encoding="utf-8",
        newline="",
    ) as handle:
        handle.write(text)


def cleanup():
    if os.path.isdir(ROOT):
        shutil.rmtree(ROOT)


def prepare():
    cleanup()

    os.makedirs(
        ROOT + "/canonical",
        exist_ok=True,
    )

    write_text(
        ROOT + "/dailydialog/dialogues.json",
        (
            '[{"dialogue":["Hello  there","Hi!"],'
            '"act":[1,2],"emotion":[0,1]}]'
        ),
    )

    write_text(
        ROOT + "/dailydialog/ontology.json",
        (
            '{"acts":{"1":"inform"},'
            '"emotions":{"0":"neutral"}}'
        ),
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
        (
            '{"A":{"name":"Alice"},'
            '"B":{"name":"Bob"}}'
        ),
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
            '"parent_id":null,"role":"prompter",'
            '"text":"Hello","lang":"en"}\n'
            '{"message_id":"m2","message_tree_id":"t1",'
            '"parent_id":"m1","role":"assistant",'
            '"text":"Hi","lang":"en"}\n'
        ),
    )


def source_map(dataset_id):
    maps = {
        "dailydialog": {
            "dialogues": (
                ROOT + "/dailydialog/dialogues.json"
            ),
            "ontology": (
                ROOT + "/dailydialog/ontology.json"
            ),
        },
        "dolly": {
            "instructions": (
                ROOT + "/dolly/data.jsonl"
            ),
        },
        "movie-corpus": {
            "conversations": (
                ROOT + "/movie/conversations.json"
            ),
            "corpus": (
                ROOT + "/movie/corpus.json"
            ),
            "index": (
                ROOT + "/movie/index.json"
            ),
            "speakers": (
                ROOT + "/movie/speakers.json"
            ),
            "utterances": (
                ROOT + "/movie/utterances.json"
            ),
        },
        "siresoft": {
            "knowledge": (
                ROOT + "/siresoft/siresoft.txt"
            ),
        },
        "tinystories": {
            "stories": (
                ROOT + "/tinystories/stories.txt"
            ),
        },
        "openassistant": {
            "messages": (
                ROOT + "/openassistant/oasst.jsonl"
            ),
        },
    }

    return maps[dataset_id]


def full_config():
    ids = [
        "dailydialog",
        "dolly",
        "movie-corpus",
        "siresoft",
        "tinystories",
        "openassistant",
    ]

    datasets = []

    for dataset_id in ids:
        datasets.append(
            DatasetPreprocessingConfig(
                dataset_id=dataset_id,
                sources=source_map(
                    dataset_id
                ),
                normalize=True,
                strict=True,
                output_path=(
                    ROOT
                    + "/canonical/"
                    + dataset_id
                    + ".jsonl"
                ),
            )
        )

    return PreprocessingConfig(
        datasets=datasets,
        allow_default_sources=False,
        require_canonical_outputs=True,
    )


def test_dataset_config():
    item = DatasetPreprocessingConfig(
        "siresoft",
        sources={
            "knowledge": "x.txt",
        },
        normalize=False,
        strict=False,
    )

    eq(
        item.required_roles(),
        ["knowledge"],
        "required source role map",
    )

    eq(
        item.normalize,
        False,
        "normalization flag preserved",
    )

    expect_error(
        ValueError,
        lambda: DatasetPreprocessingConfig(
            "unknown"
        ),
        "unsupported dataset rejected",
    )


def test_default_plan():
    config = default_preprocessing_config()

    eq(
        len(config.datasets),
        6,
        "default preprocessing plan includes all six datasets",
    )

    eq(
        config.dataset_map()[
            "siresoft"
        ].output_path,
        (
            "datasets/canonical/"
            "siresoft.jsonl"
        ),
        "SireSoft canonical output path",
    )

    eq(
        config.require_canonical_outputs,
        True,
        "default plan requires canonical outputs",
    )


def test_codec():
    text = (
        '{"datasets":['
        '{"dataset_id":"siresoft",'
        '"sources":{"knowledge":"raw/company.txt"},'
        '"normalize":true,"strict":true,'
        '"output_path":"canonical/company.jsonl"}'
        '],'
        '"allow_default_sources":false,'
        '"require_canonical_outputs":true,'
        '"metadata":{"profile":"test"}}'
    )

    config = (
        PreprocessingConfigCodec()
        .decode_text(text)
    )

    eq(
        config.datasets[0]
        .sources["knowledge"],
        "raw/company.txt",
        "codec source map",
    )

    eq(
        config.datasets[0].strict,
        True,
        "codec strict validation flag",
    )

    eq(
        config.metadata["profile"],
        "test",
        "codec metadata",
    )


def test_raw_output_protection():
    config = PreprocessingConfig(
        datasets=[
            DatasetPreprocessingConfig(
                "siresoft",
                sources={
                    "knowledge": (
                        "datasets/raw/siresoft/siresoft.txt"
                    ),
                },
                output_path=(
                    "datasets/raw/siresoft/siresoft.txt"
                ),
            ),
        ],
    )

    result = (
        PreprocessingConfigValidator()
        .validate(config)
    )

    eq(
        result["valid"],
        False,
        "preprocessing cannot target immutable raw path",
    )

    eq(
        result["errors"][0]["code"],
        "RAW_LAYER_OUTPUT_FORBIDDEN",
        "raw-layer protection error code",
    )


def test_missing_source_validation():
    config = PreprocessingConfig(
        datasets=[
            DatasetPreprocessingConfig(
                "dolly",
                sources={},
            ),
        ],
        allow_default_sources=False,
    )

    result = (
        PreprocessingConfigValidator()
        .validate(config)
    )

    eq(
        result["valid"],
        False,
        "missing required source invalid when defaults disabled",
    )

    eq(
        result["errors"][0]["code"],
        "MISSING_REQUIRED_SOURCE_ROLE",
        "missing source validation code",
    )


def test_real_six_dataset_run():
    config = full_config()

    result = (
        PreprocessingConfigFactory()
        .process_all(config)
    )

    eq(
        result["dataset_count"],
        6,
        "all six preprocessing plans executed",
    )

    eq(
        result["record_count"],
        13,
        "all canonical records preserved across six datasets",
    )

    eq(
        result["document_count"],
        9,
        "training-eligible documents bridged without auxiliary leakage",
    )

    eq(
        result["valid"],
        True,
        "all configured canonical records validate",
    )

    for item in config.enabled_datasets():
        check(
            os.path.isfile(
                item.output_path
            ),
            "canonical JSONL created for "
            + item.dataset_id,
        )


def test_loss_preserving_normalization():
    config = full_config()
    factory = PreprocessingConfigFactory()
    pipeline = factory.build_pipeline(
        config
    )

    result = factory.process_dataset(
        pipeline,
        config,
        "siresoft",
    )

    record = result.records[0]

    eq(
        record.raw_content,
        (
            "SireSoft  builds “professional” software.\n"
            "It serves clients."
        ),
        "raw SireSoft source remains unchanged",
    )

    eq(
        record.normalized_content,
        (
            'SireSoft builds "professional" software.\n'
            "It serves clients."
        ),
        "model-facing text normalized separately",
    )

    check(
        len(record.preprocessing_history)
        >= 1,
        "normalization provenance recorded",
    )


def test_auxiliary_preservation():
    config = full_config()
    factory = PreprocessingConfigFactory()

    result = factory.process_dataset(
        factory.build_pipeline(
            config
        ),
        config,
        "dailydialog",
    )

    ids = [
        record.record_id
        for record in result.records
    ]

    check(
        "dailydialog-ontology"
        in ids,
        "DailyDialog ontology preserved as auxiliary canonical record",
    )

    eq(
        len(result.documents),
        1,
        "auxiliary ontology excluded from training document bridge",
    )


def test_service_generation():
    config = full_config()

    service = (
        PreprocessingConfigFactory()
        .build_service(config)
    )

    response = service.handle(
        ServiceRequest(
            "pre-cfg-preview",
            "preprocessing_service",
            "preview",
            payload={
                "dataset_id": (
                    "openassistant"
                ),
                "sources": source_map(
                    "openassistant"
                ),
                "strict": True,
            },
        )
    )

    eq(
        response.success,
        True,
        "configured preprocessing service responds",
    )

    eq(
        response.data[
            "summary"
        ][
            "record_count"
        ],
        1,
        "configured service uses real OASST loader",
    )


def test_disabled_dataset():
    config = PreprocessingConfig(
        datasets=[
            DatasetPreprocessingConfig(
                "siresoft",
                sources=source_map(
                    "siresoft"
                ),
                enabled=False,
            ),
            DatasetPreprocessingConfig(
                "dolly",
                sources=source_map(
                    "dolly"
                ),
                enabled=True,
            ),
        ],
    )

    factory = PreprocessingConfigFactory()

    result = factory.process_all(
        config
    )

    eq(
        result["dataset_count"],
        1,
        "disabled preprocessing dataset skipped",
    )

    expect_error(
        ValueError,
        lambda: factory.process_dataset(
            factory.build_pipeline(
                config
            ),
            config,
            "siresoft",
        ),
        "explicit execution of disabled dataset rejected",
    )


def test_normalization_disabled_warning():
    config = PreprocessingConfig(
        datasets=[
            DatasetPreprocessingConfig(
                "siresoft",
                sources=source_map(
                    "siresoft"
                ),
                normalize=False,
                strict=False,
            ),
        ],
    )

    result = (
        PreprocessingConfigValidator()
        .validate(config)
    )

    codes = [
        item["code"]
        for item in result[
            "warnings"
        ]
    ]

    check(
        "NORMALIZATION_DISABLED"
        in codes,
        "disabled normalization warned",
    )

    check(
        "NON_STRICT_CANONICAL_VALIDATION"
        in codes,
        "non-strict validation warned",
    )


def main():
    prepare()

    try:
        test_dataset_config()
        test_default_plan()
        test_codec()
        test_raw_output_protection()
        test_missing_source_validation()
        test_real_six_dataset_run()
        test_loss_preserving_normalization()
        test_auxiliary_preservation()
        test_service_generation()
        test_disabled_dataset()
        test_normalization_disabled_warning()

    finally:
        cleanup()

    print(
        "PREPROCESSING CONFIG TEST SUITE: PASS"
    )
    print(
        "Assertions passed:",
        ASSERTIONS,
    )
    print(
        "Files validated: 6/6"
    )
    print(
        "Six-dataset preprocessing plan: VALIDATED"
    )
    print(
        "Immutable raw-layer protection: VALIDATED"
    )
    print(
        "Handwritten JSON decoding: VALIDATED"
    )
    print(
        "Required-source validation: VALIDATED"
    )
    print(
        "Real raw -> canonical pipeline: VALIDATED"
    )
    print(
        "Loss-preserving normalization/history: VALIDATED"
    )
    print(
        "Auxiliary-data preservation: VALIDATED"
    )
    print(
        "Canonical JSONL export: VALIDATED"
    )
    print(
        "PreprocessingService generation: VALIDATED"
    )
    print(
        "Third-party dependencies: 0"
    )


main()
