import sys
from pathlib import Path


ROOT = Path(
    __file__
).resolve().parents[1]

TESTS = Path(
    __file__
).resolve().parent

sys.path.insert(
    0,
    str(
        TESTS
    ),
)

from system_manifest import (
    EXPECTED_FOLDERS,
    TEST_FILE_BY_FOLDER,
    CRITICAL_FILES,
    SMOKE_TESTS,
)
from repository_validator import (
    RepositoryValidator,
)
from integration_runner import (
    IntegrationRunner,
)


ASSERTIONS = 0


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
        (
            message
            + " | got="
            + repr(
                actual
            )
            + " expected="
            + repr(
                expected
            )
        ),
    )


def test_manifest():
    expected_count = len(EXPECTED_FOLDERS)

    check(
        expected_count >= 100,
        "canonical internal folder manifest is unexpectedly small",
    )

    eq(
        len(TEST_FILE_BY_FOLDER),
        expected_count,
        "canonical test mapping count matches folder manifest",
    )

    eq(
        EXPECTED_FOLDERS[
            -1
        ],
        "tests",
        "tests is final internal folder",
    )

    eq(
        len(set(EXPECTED_FOLDERS)),
        len(EXPECTED_FOLDERS),
        "folder manifest contains no duplicates",
    )

    eq(
        set(
            EXPECTED_FOLDERS
        ),
        set(
            TEST_FILE_BY_FOLDER
        ),
        "test mapping exactly matches folder manifest",
    )


def test_repository_validation():
    result = (
        RepositoryValidator(
            ROOT,
            EXPECTED_FOLDERS,
            CRITICAL_FILES,
            TEST_FILE_BY_FOLDER,
        )
        .validate_all()
    )

    if not result[
        "valid"
    ]:
        raise AssertionError(
            (
                "complete repository validation failed | "
                + repr(
                    result
                )
            )
        )

    eq(
        result[
            "structure"
        ][
            "missing_folders"
        ],
        [],
        "no planned folder missing",
    )

    eq(
        result[
            "structure"
        ][
            "missing_files"
        ],
        [],
        "no critical project file missing",
    )

    eq(
        result["folder_test_coverage"]["covered_folder_count"],
        len(EXPECTED_FOLDERS),
        "every internal folder has its mapped direct test",
    )

    eq(
        result[
            "folder_test_coverage"
        ][
            "uncovered_folders"
        ],
        [],
        "no internal folder lacks its mapped direct test",
    )

    eq(
        result[
            "imports"
        ][
            "external_roots"
        ],
        [],
        "repository has no unknown third-party import roots",
    )

    eq(
        result[
            "imports"
        ][
            "parse_errors"
        ],
        [],
        "all Python files parse successfully",
    )

    eq(
        result["imports"]["forbidden_ml_roots"],
        [],
        "no forbidden ML/numerical framework imports",
    )

    check(
        result[
            "frontend"
        ][
            "valid"
        ],
        "frontend integration contract valid",
    )

    check(
        result[
            "gateway"
        ][
            "valid"
        ],
        "gateway integration contract valid",
    )


def test_cross_layer_smoke():
    result = (
        IntegrationRunner(
            ROOT,
            timeout_seconds=25,
        )
        .run(
            SMOKE_TESTS,
            stop_on_failure=True,
        )
    )

    if not result[
        "all_passed"
    ]:
        failed = [
            item
            for item
            in result[
                "results"
            ]
            if not item[
                "passed"
            ]
        ]

        detail = (
            failed[
                0
            ]
            if failed
            else {}
        )

        raise AssertionError(
            (
                "cross-layer smoke failure: "
                + repr(
                    detail.get(
                        "path"
                    )
                )
                + "\nstdout:\n"
                + str(
                    detail.get(
                        "stdout",
                        "",
                    )
                )[
                    -2000:
                ]
                + "\nstderr:\n"
                + str(
                    detail.get(
                        "stderr",
                        "",
                    )
                )[
                    -2000:
                ]
            )
        )

    eq(
        result[
            "executed_count"
        ],
        len(
            SMOKE_TESTS
        ),
        "all curated smoke tests executed",
    )

    eq(
        result[
            "passed_count"
        ],
        len(
            SMOKE_TESTS
        ),
        "all curated smoke tests passed",
    )

    eq(
        result[
            "failed_count"
        ],
        0,
        "curated smoke suite has no failures",
    )


def main():
    test_manifest()
    test_repository_validation()
    test_cross_layer_smoke()

    print(
        "SYSTEM INTEGRATION TEST SUITE: PASS"
    )
    print(
        "Assertions passed:",
        ASSERTIONS,
    )
    print(
        "Internal architecture folders:",
        str(len(EXPECTED_FOLDERS)) + "/" + str(len(EXPECTED_FOLDERS)),
    )
    print(
        "Direct mapped test coverage:",
        str(len(EXPECTED_FOLDERS)) + "/" + str(len(EXPECTED_FOLDERS)),
    )
    print(
        "Critical file contracts: VALIDATED"
    )
    print(
        "Python syntax/import audit: VALIDATED"
    )
    print(
        "Unknown third-party import roots: 0"
    )
    print(
        "Gateway /v1/health + /v1/chat contract: VALIDATED"
    )
    print(
        "Frontend React/Vite + FastAPI contract: VALIDATED"
    )
    print(
        "Cross-layer smoke tests passed:",
        len(
            SMOKE_TESTS
        ),
        "/",
        len(
            SMOKE_TESTS
        ),
    )
    print(
        "Forbidden ML/numerical dependencies: 0"
    )
    print(
        "Allowed app runtime dependencies: fastapi, pydantic, uvicorn"
    )


main()
