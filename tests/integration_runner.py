import subprocess
import sys
import time
from pathlib import Path


class IntegrationRunner:
    def __init__(
        self,
        root,
        timeout_seconds=25,
        python_executable=None,
    ):
        if (
            not isinstance(
                timeout_seconds,
                int,
            )
            or timeout_seconds <= 0
        ):
            raise ValueError(
                "timeout_seconds must be positive int"
            )

        self.root = Path(
            root
        ).resolve()

        self.timeout_seconds = (
            timeout_seconds
        )

        self.python_executable = (
            sys.executable
            if python_executable
            is None
            else python_executable
        )

    def run(
        self,
        relative_paths,
        stop_on_failure=True,
    ):
        paths = tuple(
            relative_paths
        )

        results = []
        started = time.monotonic()

        for relative in paths:
            path = (
                self.root
                / relative
            )

            if not path.is_file():
                results.append({
                    "path": relative,
                    "passed": False,
                    "returncode": None,
                    "timed_out": False,
                    "duration_seconds": 0.0,
                    "stdout": "",
                    "stderr": (
                        "test file not found"
                    ),
                })

                if stop_on_failure:
                    break

                continue

            test_started = (
                time.monotonic()
            )

            try:
                completed = (
                    subprocess.run(
                        [
                            self.python_executable,
                            str(
                                path
                            ),
                        ],
                        cwd=self.root,
                        capture_output=True,
                        text=True,
                        timeout=(
                            self.timeout_seconds
                        ),
                    )
                )

                result = {
                    "path": relative,
                    "passed": (
                        completed.returncode
                        == 0
                    ),
                    "returncode": (
                        completed.returncode
                    ),
                    "timed_out": False,
                    "duration_seconds": (
                        time.monotonic()
                        - test_started
                    ),
                    "stdout": (
                        completed.stdout
                    ),
                    "stderr": (
                        completed.stderr
                    ),
                }

            except subprocess.TimeoutExpired as error:
                result = {
                    "path": relative,
                    "passed": False,
                    "returncode": None,
                    "timed_out": True,
                    "duration_seconds": (
                        time.monotonic()
                        - test_started
                    ),
                    "stdout": (
                        error.stdout
                        if isinstance(
                            error.stdout,
                            str,
                        )
                        else ""
                    ),
                    "stderr": (
                        error.stderr
                        if isinstance(
                            error.stderr,
                            str,
                        )
                        else ""
                    ),
                }

            results.append(
                result
            )

            if (
                stop_on_failure
                and not result[
                    "passed"
                ]
            ):
                break

        return {
            "requested_count": len(
                paths
            ),
            "executed_count": len(
                results
            ),
            "passed_count": sum(
                1
                for item
                in results
                if item[
                    "passed"
                ]
            ),
            "failed_count": sum(
                1
                for item
                in results
                if not item[
                    "passed"
                ]
            ),
            "all_passed": (
                len(
                    results
                ) == len(
                    paths
                )
                and all(
                    item[
                        "passed"
                    ]
                    for item
                    in results
                )
            ),
            "duration_seconds": (
                time.monotonic()
                - started
            ),
            "results": results,
        }
