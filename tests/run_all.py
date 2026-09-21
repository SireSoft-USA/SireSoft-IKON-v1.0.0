import argparse
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
    SMOKE_TESTS,
)
from repository_validator import (
    RepositoryValidator,
)
from integration_runner import (
    IntegrationRunner,
)


def all_mapped_tests():
    ordered = []

    for folder in EXPECTED_FOLDERS:
        relative = (
            TEST_FILE_BY_FOLDER[
                folder
            ]
        )

        if relative == (
            "tests/"
            "test_system_integration.py"
        ):
            continue

        if relative not in ordered:
            ordered.append(
                relative
            )

    return tuple(
        ordered
    )


def main(
    argv=None,
):
    parser = argparse.ArgumentParser(
        prog="sirellm-tests",
        description=(
            "Validate SireLLM and run smoke or complete mapped tests."
        ),
    )

    group = (
        parser
        .add_mutually_exclusive_group()
    )

    group.add_argument(
        "--smoke",
        action="store_true",
        help=(
            "Run curated cross-layer smoke tests."
        ),
    )

    group.add_argument(
        "--all",
        action="store_true",
        help=(
            "Run all mapped folder tests except the integration test itself."
        ),
    )

    parser.add_argument(
        "--continue-on-failure",
        action="store_true",
    )

    parser.add_argument(
        "--json",
        action="store_true",
    )

    args = parser.parse_args(
        argv
    )

    validation = (
        RepositoryValidator(
            ROOT,
            EXPECTED_FOLDERS,
            CRITICAL_FILES,
            TEST_FILE_BY_FOLDER,
        )
        .validate_all()
    )

    selected = (
        all_mapped_tests()
        if args.all
        else SMOKE_TESTS
    )

    run = (
        IntegrationRunner(
            ROOT,
            timeout_seconds=25,
        )
        .run(
            selected,
            stop_on_failure=(
                not args
                .continue_on_failure
            ),
        )
    )

    result = {
        "validation": validation,
        "test_run": run,
        "passed": (
            validation[
                "valid"
            ]
            and run[
                "all_passed"
            ]
        ),
    }

    if args.json:
        print(
            json.dumps(
                result,
                indent=2,
                sort_keys=True,
            )
        )

    else:
        print(
            "Repository validation:",
            (
                "PASS"
                if validation[
                    "valid"
                ]
                else "FAIL"
            ),
        )

        print(
            "Tests:",
            (
                str(
                    run[
                        "passed_count"
                    ]
                )
                + "/"
                + str(
                    run[
                        "executed_count"
                    ]
                )
                + " passed"
            ),
        )

        if not run[
            "all_passed"
        ]:
            for item in run[
                "results"
            ]:
                if not item[
                    "passed"
                ]:
                    print(
                        "FAILED:",
                        item[
                            "path"
                        ],
                    )
                    break

    return (
        0
        if result[
            "passed"
        ]
        else 1
    )


if __name__ == "__main__":
    raise SystemExit(
        main()
    )
