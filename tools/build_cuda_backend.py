"""Build SireSoft-IKON's custom CUDA backend.

nvcc is a build-time dependency only.  If a usable prebuilt backend already
exists, runtime training does not require nvcc.  In non-required mode this
script exits cleanly when no compiler is available so the auto-device pipeline
can continue on CPU instead of crashing during a CUDA build precheck.
"""

import argparse
import os
import subprocess
from pathlib import Path

from real_runtime import ROOT, enter_project_root
from cuda_status import CUDA_LIBRARY, CUDA_SOURCE, nvcc_info


def main():
    parser = argparse.ArgumentParser(
        description="Compile the custom SireSoft-IKON CUDA compute backend."
    )
    parser.add_argument(
        "--arch",
        default=os.getenv("SIREIKON_CUDA_ARCH", "sm_61"),
        help="CUDA architecture. Quadro P5000 uses sm_61.",
    )
    parser.add_argument(
        "--nvcc",
        default=os.getenv("NVCC"),
        help="Optional explicit path/name of NVIDIA nvcc compiler.",
    )
    parser.add_argument(
        "--required",
        action="store_true",
        help="Fail if the CUDA backend cannot be built. Default is non-fatal.",
    )
    parser.add_argument("--verbose", action="store_true")
    args = parser.parse_args()

    enter_project_root()

    compiler = nvcc_info(args.nvcc)
    nvcc = compiler.get("path")

    if not compiler.get("available"):
        if CUDA_LIBRARY.is_file() and CUDA_LIBRARY.stat().st_size > 0:
            print("[OK] nvcc is not available, but a prebuilt CUDA backend exists.")
            print("runtime library:", CUDA_LIBRARY)
            print("No rebuild is required for runtime CUDA use.")
            return 0

        message = (
            "CUDA compiler is not available and no prebuilt SireSoft-IKON CUDA "
            "backend was found. nvcc is required only to build libsireikon_cuda.so."
        )
        if args.required:
            raise SystemExit(message)
        print("[SKIP]", message)
        print("Auto-device mode can continue with the handwritten CPU backend.")
        return 0

    version_text = compiler.get("version_text") or ""
    major = compiler.get("major")
    print(version_text)
    print()

    if args.arch == "sm_61" and major is not None and major >= 13:
        message = (
            "This nvcc is CUDA Toolkit 13+ and cannot offline-compile Pascal sm_61. "
            "A CUDA 12.x compiler or a prebuilt sm_61 backend is required."
        )
        if CUDA_LIBRARY.is_file() and CUDA_LIBRARY.stat().st_size > 0:
            print("[OK]", message)
            print("Using existing prebuilt backend:", CUDA_LIBRARY)
            return 0
        if args.required:
            raise SystemExit(message)
        print("[SKIP]", message)
        return 0

    source = CUDA_SOURCE
    output = CUDA_LIBRARY
    if not source.is_file():
        raise SystemExit("CUDA source file is missing: " + str(source))

    command = [
        str(nvcc),
        "-O3",
        "-std=c++14",
        "--shared",
        "-Xcompiler",
        "-fPIC",
        "-arch=" + args.arch,
        str(source),
        "-o",
        str(output),
    ]

    print("Building custom CUDA backend")
    print("architecture:", args.arch)
    print("compiler:", nvcc)
    print("source:", source)
    print("output:", output)
    if args.verbose:
        print("command:", " ".join(command))
    print()

    completed = subprocess.run(command, cwd=ROOT)
    if completed.returncode != 0:
        if args.required:
            raise SystemExit(completed.returncode)
        print("[WARN] CUDA backend build failed; auto-device mode may use CPU.")
        return completed.returncode

    if not output.is_file() or output.stat().st_size == 0:
        message = "CUDA build command completed but shared library is missing."
        if args.required:
            raise SystemExit(message)
        print("[WARN]", message)
        return 1

    print("CUDA BACKEND BUILD COMPLETE")
    print(output)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
