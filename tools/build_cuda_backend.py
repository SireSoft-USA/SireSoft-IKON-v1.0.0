"""Developer/CI build tool for SireSoft-IKON's CUDA backend.

This command is intentionally NOT called by ``run_pipeline.py``.  Production
training consumes a precompiled Linux ``libsireikon_cuda.so`` and never needs
``nvcc`` on the server.

A GPU is not required to compile.  A Linux x86_64 environment with CUDA 12.x
``nvcc`` is required for the Quadro P5000 / Pascal ``sm_61`` target.
"""

import argparse
import os
import platform
import re
import subprocess
import sys

from cuda_status import CUDA_LIBRARY, CUDA_SOURCE, nvcc_info
from real_runtime import ROOT, enter_project_root


def toolkit_release(version_text):
    match = re.search(r"release\s+([0-9]+(?:\.[0-9]+)?)", version_text or "")
    return match.group(1) if match else "unknown"


def main():
    parser = argparse.ArgumentParser(description="Compile the Linux SireSoft-IKON CUDA backend.")
    parser.add_argument("--arch", default=os.getenv("SIREIKON_CUDA_ARCH", "sm_61"))
    parser.add_argument("--nvcc", default=os.getenv("NVCC"))
    parser.add_argument("--required", action="store_true")
    parser.add_argument("--verbose", action="store_true")
    args = parser.parse_args()

    enter_project_root()

    if sys.platform != "linux" or platform.machine().lower() not in ("x86_64", "amd64"):
        message = (
            "The deployment backend must be built as linux-x86_64. "
            "Use the included GitHub Actions workflow, or run this command inside Linux/WSL with CUDA 12.x."
        )
        if args.required:
            raise SystemExit(message)
        print("[SKIP]", message)
        return 0

    compiler = nvcc_info(args.nvcc)
    nvcc = compiler.get("path")
    if not compiler.get("available"):
        message = (
            "nvcc is not available. Runtime training does not need nvcc; build the backend in GitHub Actions "
            "or on a Linux x86_64 development machine with CUDA 12.x."
        )
        if args.required:
            raise SystemExit(message)
        print("[SKIP]", message)
        return 0

    major = compiler.get("major")
    if args.arch == "sm_61" and major is not None and major >= 13:
        raise SystemExit(
            "CUDA Toolkit 13+ cannot offline-compile the Pascal sm_61 deployment target. "
            "Use CUDA 12.x."
        )

    if not CUDA_SOURCE.is_file():
        raise SystemExit("CUDA source file is missing: " + str(CUDA_SOURCE))

    command = [
        str(nvcc),
        "-O3",
        "-std=c++14",
        "--shared",
        "--cudart=static",
        "-Xcompiler=-fPIC",
        "-gencode=arch=compute_61,code=sm_61" if args.arch == "sm_61" else "-arch=" + args.arch,
        str(CUDA_SOURCE),
        "-o",
        str(CUDA_LIBRARY),
    ]
    if args.arch == "sm_61":
        command.insert(-3, "-gencode=arch=compute_61,code=compute_61")

    print("Building SireSoft-IKON CUDA backend")
    print("target: linux-x86_64")
    print("architecture:", args.arch)
    print("compiler:", nvcc)
    if args.verbose:
        print("command:", " ".join(command))
    print()

    completed = subprocess.run(command, cwd=ROOT)
    if completed.returncode != 0:
        if args.required:
            raise SystemExit(completed.returncode)
        print("[WARN] CUDA backend build failed.")
        return completed.returncode

    if not CUDA_LIBRARY.is_file() or CUDA_LIBRARY.stat().st_size == 0:
        raise SystemExit("CUDA build completed but libsireikon_cuda.so was not produced.")

    release = toolkit_release(compiler.get("version_text"))
    metadata_command = [
        sys.executable,
        str(ROOT / "tools" / "write_cuda_build_metadata.py"),
        "--arch",
        args.arch,
        "--toolkit",
        release,
        "--builder",
        "local-nvcc",
    ]
    metadata = subprocess.run(metadata_command, cwd=ROOT)
    if metadata.returncode != 0:
        raise SystemExit(metadata.returncode)

    print("CUDA BACKEND BUILD COMPLETE")
    print(CUDA_LIBRARY)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
