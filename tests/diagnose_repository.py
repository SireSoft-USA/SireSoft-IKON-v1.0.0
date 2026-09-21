import json
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
)
from repository_validator import (
    RepositoryValidator,
)


def main():
    result = (
        RepositoryValidator(
            ROOT,
            EXPECTED_FOLDERS,
            CRITICAL_FILES,
            TEST_FILE_BY_FOLDER,
        )
        .validate_all()
    )

    print(
        "SireLLM repository diagnosis"
    )
    print(
        "Overall:",
        (
            "PASS"
            if result[
                "valid"
            ]
            else "FAIL"
        ),
    )

    structure = result[
        "structure"
    ]

    print(
        "Folders:",
        (
            str(
                structure[
                    "expected_folder_count"
                ]
                - len(
                    structure[
                        "missing_folders"
                    ]
                )
            )
            + "/"
            + str(
                structure[
                    "expected_folder_count"
                ]
            )
        ),
    )

    coverage = result[
        "folder_test_coverage"
    ]

    print(
        "Direct test coverage:",
        (
            str(
                coverage[
                    "covered_folder_count"
                ]
            )
            + "/"
            + str(
                len(
                    EXPECTED_FOLDERS
                )
            )
        ),
    )

    if structure[
        "missing_folders"
    ]:
        print(
            "Missing folders:"
        )

        for item in structure[
            "missing_folders"
        ]:
            print(
                "  -",
                item,
            )

    if structure[
        "missing_files"
    ]:
        print(
            "Missing critical files:"
        )

        for item in structure[
            "missing_files"
        ]:
            print(
                "  -",
                item,
            )

    if coverage[
        "uncovered_folders"
    ]:
        print(
            "Folders without their expected direct test file:"
        )

        for item in coverage[
            "uncovered_folders"
        ]:
            print(
                "  -",
                item,
                "=>",
                TEST_FILE_BY_FOLDER.get(
                    item,
                    "<no mapping>",
                ),
            )

    if coverage[
        "manifest_errors"
    ]:
        print(
            "Test manifest errors:"
        )

        for item in coverage[
            "manifest_errors"
        ]:
            print(
                "  -",
                item,
            )

    imports = result[
        "imports"
    ]

    print(
        "Python files parsed:",
        imports[
            "python_file_count"
        ],
    )

    if imports[
        "external_roots"
    ]:
        print(
            "Unknown import roots:"
        )

        for item in imports[
            "external_roots"
        ]:
            print(
                "  -",
                item,
            )

    if imports[
        "parse_errors"
    ]:
        print(
            "Python parse errors:"
        )

        for item in imports[
            "parse_errors"
        ]:
            print(
                "  -",
                item[
                    "path"
                ],
                "=>",
                item[
                    "error"
                ],
            )

    failed_frontend = [
        key
        for key, value
        in result[
            "frontend"
        ][
            "checks"
        ].items()
        if not value
    ]

    if failed_frontend:
        print(
            "Frontend contract failures:"
        )

        for item in failed_frontend:
            print(
                "  -",
                item,
            )

    if result[
        "gateway"
    ][
        "missing_routes"
    ]:
        print(
            "Missing gateway routes:"
        )

        for item in result[
            "gateway"
        ][
            "missing_routes"
        ]:
            print(
                "  -",
                item,
            )

    print()
    print(
        json.dumps(
            result,
            indent=2,
            sort_keys=True,
        )
    )

    return (
        0
        if result[
            "valid"
        ]
        else 1
    )


if __name__ == "__main__":
    raise SystemExit(
        main()
    )
