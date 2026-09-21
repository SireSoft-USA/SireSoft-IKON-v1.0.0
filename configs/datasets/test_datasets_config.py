import os
import shutil

PARSERS_BASE = "libs/data/parsers/"
PROTOCOL_BASE = "libs/protocol/"
SERVICE_BASE = "services/dataset_service/"
CONFIG_BASE = "configs/datasets/"

namespace = {
    "__builtins__": __builtins__,
}

groups = [
    (
        PARSERS_BASE,
        [
            "json_parser.py",
        ],
    ),
    (
        PROTOCOL_BASE,
        [
            "error.py",
            "message.py",
            "request.py",
            "response.py",
        ],
    ),
    (
        SERVICE_BASE,
        [
            "manifest.py",
            "catalog.py",
            "snapshot.py",
            "inspector.py",
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
    "source.py",
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
            "datasets config implementation contains forbidden import: "
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

globals().update(
    namespace
)

ASSERTIONS = 0

TEST_ROOT = (
    "configs/datasets/_test_raw"
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


def cleanup():
    if os.path.isdir(
        TEST_ROOT
    ):
        shutil.rmtree(
            TEST_ROOT
        )


def prepare():
    cleanup()

    os.makedirs(
        TEST_ROOT,
        exist_ok=True,
    )

    json_path = (
        TEST_ROOT
        + "/dialogues.json"
    )

    jsonl_path = (
        TEST_ROOT
        + "/instructions.jsonl"
    )

    text_path = (
        TEST_ROOT
        + "/company.txt"
    )

    with open(
        json_path,
        "w",
        encoding="utf-8",
    ) as handle:
        handle.write(
            '[{"dialogue":["hello","hi"]}]'
        )

    with open(
        jsonl_path,
        "w",
        encoding="utf-8",
    ) as handle:
        handle.write(
            '{"instruction":"hello","response":"hi"}\n'
        )

    with open(
        text_path,
        "w",
        encoding="utf-8",
    ) as handle:
        handle.write(
            "SireSoft software knowledge."
        )

    return {
        "json": json_path,
        "jsonl": jsonl_path,
        "text": text_path,
    }


def sample_config(
    paths,
    capture=False,
):
    return DatasetsConfig(
        datasets=[
            DatasetDefinitionConfig(
                dataset_id="dialogue",
                name="Dialogue",
                sources=[
                    DatasetSourceConfig(
                        paths[
                            "json"
                        ],
                        "json",
                        role="dialogues",
                    ),
                ],
            ),
            DatasetDefinitionConfig(
                dataset_id="instruction",
                name="Instruction",
                sources=[
                    DatasetSourceConfig(
                        paths[
                            "jsonl"
                        ],
                        "jsonl",
                        role="instructions",
                    ),
                ],
            ),
            DatasetDefinitionConfig(
                dataset_id="knowledge",
                name="Knowledge",
                sources=[
                    DatasetSourceConfig(
                        paths[
                            "text"
                        ],
                        "text",
                        role="knowledge",
                    ),
                ],
                metadata={
                    "rag_eligible": True,
                },
            ),
        ],
        capture_immutable_baselines=(
            capture
        ),
    )


def test_source_config():
    source = (
        DatasetSourceConfig(
            "data/file.json",
            "json",
            role="data",
        )
    )

    eq(
        source.to_dict()[
            "format"
        ],
        "json",
        "source format serialized",
    )

    expect_error(
        ValueError,
        lambda: DatasetSourceConfig(
            "x",
            "csv",
        ),
        "unsupported source format rejected",
    )


def test_default_inventory():
    config = (
        default_datasets_config()
    )

    eq(
        len(
            config.datasets
        ),
        6,
        "finalized dataset inventory contains six dataset families",
    )

    ids = [
        dataset.dataset_id
        for dataset
        in config.datasets
    ]

    eq(
        ids,
        [
            "dailydialog",
            "dolly",
            "movie-corpus",
            "siresoft",
            "tinystories",
            "openassistant",
        ],
        "default dataset IDs preserved",
    )

    movie = config.dataset_map()[
        "movie-corpus"
    ]

    eq(
        len(
            movie.sources
        ),
        5,
        "Cornell relational source files preserved individually",
    )

    openassistant = (
        config.dataset_map()[
            "openassistant"
        ]
    )

    eq(
        len(
            openassistant.sources
        ),
        2,
        "OpenAssistant archive and extracted source both preserved",
    )

    eq(
        openassistant.sources[
            0
        ].required,
        False,
        "compressed OpenAssistant source remains optional",
    )


def test_codec():
    text = (
        '{"datasets":['
        '{"dataset_id":"one","name":"One",'
        '"sources":['
        '{"path":"a.json","format":"json","role":"data"}'
        ']},'
        '{"dataset_id":"two","name":"Two",'
        '"enabled":false,'
        '"sources":['
        '{"path":"b.txt","format":"text","required":false}'
        ']}'
        '],'
        '"enforce_global_source_uniqueness":true,'
        '"capture_immutable_baselines":false}'
    )

    config = (
        DatasetsConfigCodec()
        .decode_text(
            text
        )
    )

    eq(
        len(
            config.datasets
        ),
        2,
        "codec dataset count",
    )

    eq(
        len(
            config.enabled_datasets()
        ),
        1,
        "codec enabled dataset count",
    )

    eq(
        config.datasets[
            1
        ].sources[
            0
        ].required,
        False,
        "codec optional raw source",
    )


def test_global_source_validation():
    config = DatasetsConfig(
        datasets=[
            DatasetDefinitionConfig(
                "a",
                "A",
                [
                    DatasetSourceConfig(
                        "shared.json",
                        "json",
                    ),
                ],
            ),
            DatasetDefinitionConfig(
                "b",
                "B",
                [
                    DatasetSourceConfig(
                        "shared.json",
                        "json",
                    ),
                ],
            ),
        ],
    )

    result = (
        DatasetsConfigValidator()
        .validate(
            config
        )
    )

    eq(
        result[
            "valid"
        ],
        False,
        "reused raw source path rejected",
    )

    eq(
        result[
            "errors"
        ][0][
            "code"
        ],
        "SOURCE_PATH_REUSED",
        "source reuse validation code",
    )


def test_factory_catalog(
    paths,
):
    config = sample_config(
        paths
    )

    catalog = (
        DatasetsConfigFactory()
        .build_catalog(
            config
        )
    )

    eq(
        catalog.count(),
        3,
        "factory builds dataset catalog",
    )

    manifest = catalog.get(
        "knowledge"
    )

    eq(
        manifest.metadata[
            "rag_eligible"
        ],
        True,
        "factory preserves dataset metadata",
    )

    eq(
        manifest.sources[
            0
        ].role,
        "knowledge",
        "factory preserves raw source role",
    )


def test_real_status(
    paths,
):
    service = (
        DatasetsConfigFactory()
        .build_service(
            sample_config(
                paths
            )
        )
    )

    response = service.handle(
        ServiceRequest(
            "dataset-status",
            "dataset_service",
            "status",
            payload={
                "dataset_id": (
                    "dialogue"
                ),
            },
        )
    )

    eq(
        response.success,
        True,
        "configured dataset service status succeeds",
    )

    snapshot = response.data[
        "snapshot"
    ]

    eq(
        snapshot[
            "complete"
        ],
        True,
        "configured JSON dataset passes raw format inspection",
    )

    check(
        snapshot[
            "files"
        ][0][
            "checksum"
        ]
        is not None,
        "raw dataset inspection records immutable fingerprint",
    )


def test_immutable_baseline(
    paths,
):
    config = sample_config(
        paths,
        capture=True,
    )

    service = (
        DatasetsConfigFactory()
        .build_service(
            config
        )
    )

    check(
        service.tracker.has_baseline(
            "knowledge"
        ),
        "factory captures requested immutable baseline",
    )

    unchanged = service.handle(
        ServiceRequest(
            "verify-1",
            "dataset_service",
            "verify_immutable",
            payload={
                "dataset_id": (
                    "knowledge"
                ),
            },
        )
    )

    eq(
        unchanged.data[
            "immutable"
        ],
        True,
        "unchanged raw source passes immutable verification",
    )

    with open(
        paths[
            "text"
        ],
        "a",
        encoding="utf-8",
    ) as handle:
        handle.write(
            " MUTATED"
        )

    changed = service.handle(
        ServiceRequest(
            "verify-2",
            "dataset_service",
            "verify_immutable",
            payload={
                "dataset_id": (
                    "knowledge"
                ),
            },
        )
    )

    eq(
        changed.data[
            "immutable"
        ],
        False,
        "raw mutation detected against configuration-time baseline",
    )

    change_types = [
        item[
            "change"
        ]
        for item
        in changed.data[
            "changes"
        ]
    ]

    check(
        "checksum_changed"
        in change_types,
        "raw mutation reports checksum change",
    )


def test_service_listing(
    paths,
):
    service = (
        DatasetsConfigFactory()
        .build_service(
            sample_config(
                paths
            )
        )
    )

    response = service.handle(
        ServiceRequest(
            "dataset-list",
            "dataset_service",
            "list_datasets",
        )
    )

    eq(
        response.success,
        True,
        "configured dataset service lists datasets",
    )

    eq(
        response.data[
            "count"
        ],
        3,
        "configured dataset service count",
    )


def test_disabled_dataset_excluded(
    paths,
):
    config = DatasetsConfig(
        datasets=[
            DatasetDefinitionConfig(
                "on",
                "On",
                [
                    DatasetSourceConfig(
                        paths[
                            "json"
                        ],
                        "json",
                    ),
                ],
            ),
            DatasetDefinitionConfig(
                "off",
                "Off",
                [
                    DatasetSourceConfig(
                        paths[
                            "text"
                        ],
                        "text",
                    ),
                ],
                enabled=False,
            ),
        ],
    )

    catalog = (
        DatasetsConfigFactory()
        .build_catalog(
            config
        )
    )

    eq(
        catalog.dataset_ids(),
        [
            "on",
        ],
        "disabled dataset excluded from runtime catalog",
    )


def main():
    paths = prepare()

    try:
        test_source_config()
        test_default_inventory()
        test_codec()
        test_global_source_validation()
        test_factory_catalog(
            paths
        )
        test_real_status(
            paths
        )
        test_immutable_baseline(
            paths
        )

        # restore test data after mutation before remaining tests
        paths = prepare()

        test_service_listing(
            paths
        )
        test_disabled_dataset_excluded(
            paths
        )

    finally:
        cleanup()

    print(
        "DATASETS CONFIG TEST SUITE: PASS"
    )
    print(
        "Assertions passed:",
        ASSERTIONS,
    )
    print(
        "Files validated: 7/7"
    )
    print(
        "Final six-dataset raw inventory: VALIDATED"
    )
    print(
        "Auxiliary/source preservation: VALIDATED"
    )
    print(
        "Handwritten JSON decoding: VALIDATED"
    )
    print(
        "Cross-dataset source validation: VALIDATED"
    )
    print(
        "DatasetCatalog generation: VALIDATED"
    )
    print(
        "Real raw-file inspection/fingerprinting: VALIDATED"
    )
    print(
        "Immutable baseline mutation detection: VALIDATED"
    )
    print(
        "DatasetService generation: VALIDATED"
    )
    print(
        "Third-party dependencies: 0"
    )


main()
