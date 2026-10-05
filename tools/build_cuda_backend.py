"""Build SireSoft-IKON's custom CUDA backend without Python ML libraries.

Target server: NVIDIA Quadro P5000 (Pascal, sm_61).  CUDA Toolkit 12.x is
recommended because CUDA Toolkit 13 removed offline compilation support for
Pascal.  The installed NVIDIA driver may advertise CUDA 13 capability while a
12.x toolkit is still the correct compiler choice for this GPU.
"""

import argparse
import os
import shutil
import subprocess
import sys
from pathlib import Path

from real_runtime import ROOT, enter_project_root


def nvcc_version(nvcc):
    completed = subprocess.run(
        [nvcc, "--version"],
        capture_output=True,
        text=True,
    )
    text = (completed.stdout or "") + "\n" + (completed.stderr or "")
    major = None
    marker = "release "
    if marker in text:
        tail = text.split(marker, 1)[1]
        token = tail.split(",", 1)[0].strip()
        try:
            major = int(token.split(".", 1)[0])
        except Exception:
            major = None
    return completed.returncode, text.strip(), major


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
        default=os.getenv("NVCC", "nvcc"),
        help="Path/name of NVIDIA nvcc compiler.",
    )
    parser.add_argument("--verbose", action="store_true")
    args = parser.parse_args()

    enter_project_root()

    nvcc = shutil.which(args.nvcc) if not Path(args.nvcc).is_file() else args.nvcc
    if not nvcc:
        raise SystemExit(
            "nvcc was not found. Install/enable NVIDIA CUDA Toolkit 12.x, then rerun."
        )

    code, version_text, major = nvcc_version(nvcc)
    if code != 0:
        raise SystemExit("Unable to run nvcc:\n" + version_text)

    print(version_text)
    print()

    if args.arch == "sm_61" and major is not None and major >= 13:
        raise SystemExit(
            "CUDA Toolkit 13+ cannot offline-compile Pascal sm_61 kernels.\n"
            "Use a CUDA Toolkit 12.x nvcc (the NVIDIA driver itself may remain newer)."
        )

    source = ROOT / "libs" / "core" / "gpu" / "sireikon_cuda.cu"
    output = ROOT / "libs" / "core" / "gpu" / "libsireikon_cuda.so"

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
    print("source:", source)
    print("output:", output)
    if args.verbose:
        print("command:", " ".join(command))
    print()

    completed = subprocess.run(command, cwd=ROOT)
    if completed.returncode != 0:
        raise SystemExit(completed.returncode)

    if not output.is_file() or output.stat().st_size == 0:
        raise SystemExit("CUDA build command completed but shared library is missing.")

    print("CUDA BACKEND BUILD COMPLETE")
    print(output)
    print()
    print("CPU-only verification (works without a GPU):")
    print("  python tools/test_compute_backend.py --device cpu")
    print("GPU verification:")
    print("  python tools/test_compute_backend.py --device cuda")


if __name__ == "__main__":
    main()
