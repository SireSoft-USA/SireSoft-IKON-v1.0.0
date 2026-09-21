import os

SERIAL_BASE = "libs/core/serialization/"
PROTOCOL_BASE = "libs/protocol/"
DATASET_BASE = "services/dataset_service/"

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
    "manifest.py",
    "catalog.py",
    "snapshot.py",
    "inspector.py",
    "service.py",
]:
    path = DATASET_BASE + filename

    source = open(
        path,
        "r",
        encoding="utf-8",
    ).read()

    if "import " in source:
        raise AssertionError(
            "dataset_service implementation contains forbidden import: "
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
TEST_DIR = (
    "services/dataset_service/"
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


def write_bytes(
    path,
    data,
):
    handle = open(
        path,
        "wb",
    )

    try:
        handle.write(
            data
        )
    finally:
        handle.close()


def write_text(
    path,
    text,
):
    handle = open(
        path,
        "w",
        encoding="utf-8",
    )

    try:
        handle.write(
            text
        )
    finally:
        handle.close()


def prepare_test_files():
    os.makedirs(
        TEST_DIR,
        exist_ok=True,
    )

    write_text(
        TEST_DIR + "/dialogues.json",
        '[{"dialogue":["hello","hi"]}]',
    )

    write_text(
        TEST_DIR + "/records.jsonl",
        '{"a":1}\n{"b":2}\n',
    )

    write_text(
        TEST_DIR + "/knowledge.txt",
        "SireSoft builds software systems.\n",
    )

    write_bytes(
        TEST_DIR + "/archive.gz",
        b"\x1f\x8b\x08\x00fake-gzip-test",
    )


def cleanup_test_files():
    if os.path.isdir(
        TEST_DIR
    ):
        for name in os.listdir(
            TEST_DIR
        ):
            os.remove(
                TEST_DIR
                + "/"
                + name
            )

        os.rmdir(
            TEST_DIR
        )


def custom_catalog():
    manifest = DatasetManifest(
        dataset_id="test-dataset",
        name="Test Dataset",
        sources=[
            DatasetSource(
                TEST_DIR + "/dialogues.json",
                "json",
                role="json",
            ),
            DatasetSource(
                TEST_DIR + "/records.jsonl",
                "jsonl",
                role="jsonl",
            ),
            DatasetSource(
                TEST_DIR + "/knowledge.txt",
                "text",
                role="text",
            ),
            DatasetSource(
                TEST_DIR + "/archive.gz",
                "gzip",
                role="archive",
                required=False,
            ),
        ],
        metadata={
            "test": True,
        },
    )

    return DatasetCatalog(
        [manifest]
    )


def test_default_manifests():
    manifests = (
        default_dataset_manifests()
    )

    eq(
        len(manifests),
        6,
        "six finalized dataset families",
    )

    ids = [
        manifest.dataset_id
        for manifest in manifests
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
        "default dataset IDs",
    )

    catalog = build_default_catalog()

    eq(
        catalog.count(),
        6,
        "default catalog count",
    )

    eq(
        [
            source.path
            for source
            in catalog.get(
                "dailydialog"
            ).sources
        ],
        [
            "datasets/raw/dailydialog/dialogues.json",
            "datasets/raw/dailydialog/ontology.json",
        ],
        "DailyDialog exact source paths",
    )

    eq(
        catalog.get(
            "dolly"
        ).sources[0].path,
        "datasets/raw/dolly/databricks-dolly-15k.jsonl",
        "Dolly exact source path",
    )

    eq(
        len(
            catalog.get(
                "movie-corpus"
            ).sources
        ),
        5,
        "Cornell five source files",
    )

    eq(
        catalog.get(
            "siresoft"
        ).sources[0].path,
        "datasets/raw/siresoft/siresoft.txt",
        "SireSoft exact source path",
    )

    eq(
        catalog.get(
            "tinystories"
        ).sources[0].path,
        "datasets/raw/tinystories/TinyStories-train.txt",
        "TinyStories exact source path",
    )

    openassistant = catalog.get(
        "openassistant"
    )

    eq(
        openassistant.sources[0].source_format,
        "gzip",
        "OpenAssistant compressed source declared",
    )

    eq(
        openassistant.sources[1].path,
        "datasets/raw/openassistant/oasst1-ready.jsonl",
        "OpenAssistant extracted source path",
    )


def test_manifest_round_trip():
    manifest = DatasetManifest(
        "x",
        "Example",
        [
            DatasetSource(
                "x/data.jsonl",
                "jsonl",
                metadata={
                    "language": "en",
                },
            ),
        ],
        metadata={
            "kind": "training",
        },
    )

    restored = DatasetManifest.from_dict(
        manifest.to_dict()
    )

    eq(
        restored.to_dict(),
        manifest.to_dict(),
        "manifest dict round trip",
    )


def test_catalog_duplicate_rejected():
    manifest = DatasetManifest(
        "x",
        "X",
        [
            DatasetSource(
                "x.txt",
                "text",
            ),
        ],
    )

    catalog = DatasetCatalog(
        [manifest]
    )

    expect_error(
        ValueError,
        lambda: catalog.register(
            manifest
        ),
        "duplicate dataset registration rejected",
    )


def test_inspector_formats():
    prepare_test_files()

    inspector = RawDatasetInspector(
        chunk_size=7,
        sample_size=64,
    )

    manifest = custom_catalog().get(
        "test-dataset"
    )

    snapshot = inspector.inspect_manifest(
        manifest
    )

    eq(
        snapshot.complete(),
        True,
        "valid test dataset complete",
    )

    eq(
        len(snapshot.files),
        4,
        "all sources inspected",
    )

    for item in snapshot.files:
        check(
            item.exists,
            "test source exists: "
            + item.path,
        )

        check(
            item.sanity_ok,
            "test source format sane: "
            + item.path,
        )

        check(
            item.size_bytes > 0,
            "test source size recorded",
        )

        check(
            isinstance(
                item.checksum,
                str,
            )
            and len(
                item.checksum
            ) == 16,
            "streaming checksum recorded",
        )


def test_missing_required_source():
    source = DatasetSource(
        TEST_DIR
        + "/definitely-missing.txt",
        "text",
        required=True,
    )

    result = (
        RawDatasetInspector()
        .inspect_source(
            source
        )
    )

    eq(
        result.exists,
        False,
        "missing file reported",
    )

    eq(
        result.usable(),
        False,
        "missing required file unusable",
    )


def test_missing_optional_source():
    source = DatasetSource(
        TEST_DIR
        + "/optional-missing.gz",
        "gzip",
        required=False,
    )

    result = (
        RawDatasetInspector()
        .inspect_source(
            source
        )
    )

    eq(
        result.exists,
        False,
        "optional missing file reported",
    )

    eq(
        result.usable(),
        True,
        "missing optional source remains usable",
    )


def test_invalid_format():
    path = (
        TEST_DIR
        + "/invalid.json"
    )

    write_text(
        path,
        "not json",
    )

    snapshot = (
        RawDatasetInspector()
        .inspect_source(
            DatasetSource(
                path,
                "json",
            )
        )
    )

    eq(
        snapshot.sanity_ok,
        False,
        "invalid JSON shape fails sanity",
    )

    eq(
        snapshot.error,
        "json_invalid_start",
        "invalid JSON reason",
    )

    os.remove(
        path
    )


def test_immutable_tracker():
    inspector = RawDatasetInspector()
    tracker = ImmutableRawTracker()
    manifest = custom_catalog().get(
        "test-dataset"
    )

    first = inspector.inspect_manifest(
        manifest
    )

    tracker.capture(
        first
    )

    clean = tracker.verify(
        inspector.inspect_manifest(
            manifest
        )
    )

    eq(
        clean["immutable"],
        True,
        "unchanged raw dataset immutable",
    )

    write_text(
        TEST_DIR + "/knowledge.txt",
        "SireSoft builds changed software systems.\n",
    )

    changed = tracker.verify(
        inspector.inspect_manifest(
            manifest
        )
    )

    eq(
        changed["immutable"],
        False,
        "raw mutation detected",
    )

    change_types = [
        item["change"]
        for item in changed[
            "changes"
        ]
        if item["path"].endswith(
            "knowledge.txt"
        )
    ]

    check(
        "checksum_changed"
        in change_types,
        "checksum mutation detected",
    )


def test_dataset_service_list_manifest_status():
    prepare_test_files()

    service = DatasetService(
        catalog=custom_catalog()
    )

    list_request = ServiceRequest(
        "r1",
        "dataset_service",
        "list_datasets",
    )

    listed = service.handle(
        list_request
    )

    eq(
        listed.success,
        True,
        "list datasets succeeds",
    )

    eq(
        listed.data["count"],
        1,
        "custom catalog count",
    )

    manifest_response = service.handle(
        ServiceRequest(
            "r2",
            "dataset_service",
            "get_manifest",
            payload={
                "dataset_id": "test-dataset",
            },
        )
    )

    eq(
        manifest_response.data[
            "manifest"
        ]["dataset_id"],
        "test-dataset",
        "manifest service operation",
    )

    status = service.handle(
        ServiceRequest(
            "r3",
            "dataset_service",
            "status",
            payload={
                "dataset_id": "test-dataset",
            },
        )
    )

    eq(
        status.data[
            "snapshot"
        ]["complete"],
        True,
        "dataset status complete",
    )


def test_dataset_service_baseline_verify():
    prepare_test_files()

    service = DatasetService(
        catalog=custom_catalog()
    )

    captured = service.handle(
        ServiceRequest(
            "r1",
            "dataset_service",
            "capture_baseline",
            payload={
                "dataset_id": "test-dataset",
            },
        )
    )

    eq(
        captured.success,
        True,
        "baseline capture succeeds",
    )

    verified = service.handle(
        ServiceRequest(
            "r2",
            "dataset_service",
            "verify_immutable",
            payload={
                "dataset_id": "test-dataset",
            },
        )
    )

    eq(
        verified.data[
            "immutable"
        ],
        True,
        "service immutable verification clean",
    )

    write_text(
        TEST_DIR + "/records.jsonl",
        '{"changed":true}\n',
    )

    changed = service.handle(
        ServiceRequest(
            "r3",
            "dataset_service",
            "verify_immutable",
            payload={
                "dataset_id": "test-dataset",
            },
        )
    )

    eq(
        changed.data[
            "immutable"
        ],
        False,
        "service detects raw mutation",
    )


def test_protocol_compatibility():
    prepare_test_files()

    service = DatasetService(
        catalog=custom_catalog()
    )

    codec = ProtocolCodec()

    request = ServiceRequest(
        "protocol-request",
        "dataset_service",
        "status",
        payload={
            "dataset_id": "test-dataset",
        },
        trace_id="trace-dataset",
    )

    decoded_request = (
        codec.decode_request(
            codec.encode_request(
                request
            )
        )
    )

    response = service.handle(
        decoded_request
    )

    decoded_response = (
        codec.decode_response(
            codec.encode_response(
                response
            )
        )
    )

    eq(
        decoded_response.success,
        True,
        "dataset service works through protocol codec",
    )

    eq(
        decoded_response.trace_id,
        "trace-dataset",
        "dataset service trace preserved",
    )

    eq(
        decoded_response.data[
            "snapshot"
        ]["dataset_id"],
        "test-dataset",
        "dataset status survives binary protocol",
    )


def test_service_errors():
    service = DatasetService(
        catalog=custom_catalog()
    )

    missing = service.handle(
        ServiceRequest(
            "r",
            "dataset_service",
            "get_manifest",
            payload={
                "dataset_id": "missing",
            },
        )
    )

    eq(
        missing.success,
        False,
        "missing dataset fails",
    )

    eq(
        missing.error.code,
        "NOT_FOUND",
        "missing dataset error code",
    )

    unsupported = service.handle(
        ServiceRequest(
            "r2",
            "dataset_service",
            "unknown",
        )
    )

    eq(
        unsupported.error.code,
        "INVALID_REQUEST",
        "unsupported operation rejected",
    )

    wrong_service = service.handle(
        ServiceRequest(
            "r3",
            "rag_service",
            "status",
        )
    )

    eq(
        wrong_service.error.code,
        "INVALID_REQUEST",
        "wrong target service rejected",
    )


def test_validation():
    expect_error(
        ValueError,
        lambda: DatasetSource(
            "x",
            "unsupported",
        ),
        "unsupported source format",
    )

    expect_error(
        ValueError,
        lambda: DatasetManifest(
            "x",
            "X",
            [],
        ),
        "empty manifest rejected",
    )

    expect_error(
        ValueError,
        lambda: RawDatasetInspector(
            chunk_size=0
        ),
        "invalid inspector chunk size",
    )

    expect_error(
        TypeError,
        lambda: DatasetService(
            catalog=custom_catalog()
        ).handle(
            {}
        ),
        "non-ServiceRequest rejected",
    )


def main():
    cleanup_test_files()
    prepare_test_files()

    try:
        test_default_manifests()
        test_manifest_round_trip()
        test_catalog_duplicate_rejected()
        test_inspector_formats()
        test_missing_required_source()
        test_missing_optional_source()
        test_invalid_format()
        test_immutable_tracker()
        test_dataset_service_list_manifest_status()
        test_dataset_service_baseline_verify()
        test_protocol_compatibility()
        test_service_errors()
        test_validation()

    finally:
        cleanup_test_files()

    print(
        "DATASET SERVICE TEST SUITE: PASS"
    )
    print(
        "Assertions passed:",
        ASSERTIONS,
    )
    print(
        "Files validated: 5/5"
    )
    print(
        "Six finalized dataset manifests: VALIDATED"
    )
    print(
        "Raw-source discovery/status: VALIDATED"
    )
    print(
        "Streaming checksum fingerprints: VALIDATED"
    )
    print(
        "Format sanity checks: VALIDATED"
    )
    print(
        "Immutable raw-data tracking: VALIDATED"
    )
    print(
        "Protocol service operations: VALIDATED"
    )
    print(
        "No preprocessing/raw mutation: VALIDATED"
    )
    print(
        "Third-party dependencies: 0"
    )


main()
