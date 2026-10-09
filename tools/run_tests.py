"""Run SireSoft-IKON's script-style test files in isolated subprocesses.

The repository intentionally keeps many tests as standalone Python programs.
Running each file in its own interpreter avoids module-name collisions and
mirrors how these tests were originally authored.
"""

import argparse
import os
import subprocess
import sys
import time
from pathlib import Path

from real_runtime import ROOT, enter_project_root


QUICK_TESTS = (
    "tests/test_django_contract.py",
    "tests/test_django_http.py",
    "tests/test_frontend_api.py",
    "tests/test_gpu_backend_contract.py",
    "tools/test_compute_backend.py",
    "tools/test_gpu_training.py",
    "tools/test_training_recovery.py",
    "model_store/manifests/test_manifests.py",
    "libs/training/test_training.py",
    "libs/transformer/test_transformer.py",
    "tests/test_system_integration.py",
)


def discover_tests():
    result = []
    for path in ROOT.rglob("test*.py"):
        relative = path.relative_to(ROOT).as_posix()
        if relative == "tools/run_tests.py":
            continue
        if "__pycache__" in path.parts:
            continue
        result.append(relative)
    return sorted(result)


def run_one(relative, timeout, require_django=False):
    command = [sys.executable, str(ROOT / relative)]
    if relative == "tools/test_gpu_training.py":
        # The portable suite never builds native CUDA code. Hardware/backend
        # absence is a valid SKIP; strict CUDA is validated on the GPU server.
        command.extend(["--arch", "sm_61"])
    env = os.environ.copy()
    if require_django:
        env["SIREIKON_REQUIRE_DJANGO_TESTS"] = "1"
    started = time.time()
    try:
        completed = subprocess.run(
            command,
            cwd=ROOT,
            capture_output=True,
            text=True,
            timeout=timeout,
            env=env,
        )
        output = ((completed.stdout or "") + (completed.stderr or "")).strip()
        return completed.returncode, output, time.time() - started
    except subprocess.TimeoutExpired as error:
        output = ((error.stdout or b"") if isinstance(error.stdout, bytes) else (error.stdout or ""))
        return 124, str(output) + "\nTIMEOUT", time.time() - started


def main():
    parser = argparse.ArgumentParser(description="Run SireSoft-IKON tests in isolated processes.")
    parser.add_argument("--quick", action="store_true", help="Run the focused regression set only.")
    parser.add_argument("--timeout", type=int, default=90, help="Per-test timeout in seconds.")
    parser.add_argument("--show-pass-output", action="store_true")
    parser.add_argument("--start", type=int, default=1, help="1-based first discovered test to run.")
    parser.add_argument("--count", type=int, default=0, help="Maximum number of tests to run; 0 means all remaining.")
    parser.add_argument(
        "--require-django", action="store_true",
        help="Fail if Django is not installed (recommended before deployment).",
    )
    args = parser.parse_args()
    if args.require_django:
        try:
            import django
        except ImportError:
            print("ERROR: Django is missing; run: python -m pip install -r requirements.txt")
            return 2

    enter_project_root()
    tests = list(QUICK_TESTS if args.quick else discover_tests())
    start_index = max(0, args.start - 1)
    tests = tests[start_index:]
    if args.count > 0:
        tests = tests[:args.count]
    failures = []
    passed = 0

    print("SireSoft-IKON TEST RUNNER")
    print("mode:", "quick" if args.quick else "all")
    print("files:", len(tests))
    print()

    for index, relative in enumerate(tests, start=1):
        code, output, elapsed = run_one(relative, args.timeout, args.require_django)
        status = "PASS" if code == 0 else "FAIL"
        print(f"[{index:03d}/{len(tests):03d}] {status} {relative} ({elapsed:.2f}s)")
        if code == 0:
            passed += 1
            if args.show_pass_output and output:
                print(output)
        else:
            failures.append((relative, code, output))
            if output:
                print(output[-4000:])
        sys.stdout.flush()

    print()
    print("=" * 72)
    print("passed:", passed)
    print("failed:", len(failures))
    print("total:", len(tests))

    if failures:
        print("Failures:")
        for relative, code, _ in failures:
            print(" -", relative, "exit", code)
        return 1

    print("TEST SUITE: PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
