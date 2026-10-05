"""CUDA runtime/build status for SireSoft-IKON.

Runtime and build concerns are intentionally separated:

* The training server only needs the NVIDIA driver, a visible GPU, and the
  precompiled ``libsireikon_cuda.so`` shipped with the project.
* ``nvcc`` is only a development/CI build dependency.  ``run_pipeline.py``
  never compiles CUDA code on the server.
* Build metadata stores the SHA-256 of ``sireikon_cuda.cu`` so deployment can
  reject a stale binary instead of silently loading an ABI-mismatched build.
"""

import argparse
import ctypes.util
import hashlib
import json
import os
import shutil
import subprocess
import sys
from pathlib import Path

from real_runtime import ROOT


CUDA_SOURCE = ROOT / "libs" / "core" / "gpu" / "sireikon_cuda.cu"
CUDA_LIBRARY = ROOT / "libs" / "core" / "gpu" / "libsireikon_cuda.so"
CUDA_METADATA = ROOT / "libs" / "core" / "gpu" / "libsireikon_cuda.build.json"
DEFAULT_ARCH = "sm_61"


def _run(command):
    try:
        completed = subprocess.run(
            command,
            cwd=ROOT,
            capture_output=True,
            text=True,
            timeout=15,
        )
    except Exception as error:
        return 1, str(error)
    text = ((completed.stdout or "") + (completed.stderr or "")).strip()
    return completed.returncode, text


def sha256_file(path):
    path = Path(path)
    if not path.is_file():
        return None
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        while True:
            block = handle.read(1024 * 1024)
            if not block:
                break
            digest.update(block)
    return digest.hexdigest()


def load_build_metadata():
    if not CUDA_METADATA.is_file():
        return None
    try:
        data = json.loads(CUDA_METADATA.read_text(encoding="utf-8"))
    except Exception:
        return None
    return data if isinstance(data, dict) else None


def backend_exists():
    return CUDA_LIBRARY.is_file() and CUDA_LIBRARY.stat().st_size > 0


def backend_is_current(expected_arch=DEFAULT_ARCH):
    """Return ``(ok, reason)`` for the checked-in precompiled backend."""
    if not backend_exists():
        return False, "precompiled CUDA backend is missing"

    metadata = load_build_metadata()
    if metadata is None:
        return False, "CUDA build metadata is missing or invalid"

    source_hash = sha256_file(CUDA_SOURCE)
    if not source_hash:
        return False, "CUDA source file is missing"

    built_hash = str(metadata.get("source_sha256") or "")
    if built_hash != source_hash:
        return False, "precompiled CUDA backend is stale for the current source"

    arch = str(metadata.get("architecture") or "")
    if expected_arch and arch != expected_arch:
        return False, f"CUDA backend targets {arch or 'unknown'}, expected {expected_arch}"

    target = str(metadata.get("target") or "")
    if target and target != "linux-x86_64":
        return False, f"CUDA backend target is {target}, expected linux-x86_64"

    return True, "precompiled CUDA backend matches the current source"


def find_nvcc(requested=None):
    """Find nvcc for developer/CI builds. Runtime training does not use it."""
    candidates = []
    if requested:
        candidates.append(str(requested))
    env_nvcc = os.getenv("NVCC")
    if env_nvcc:
        candidates.append(env_nvcc)

    resolved = shutil.which("nvcc")
    if resolved:
        candidates.append(resolved)

    candidates.extend([
        "/usr/local/cuda/bin/nvcc",
        "/opt/cuda/bin/nvcc",
    ])

    for parent in (Path("/usr/local"), Path("/opt")):
        if parent.is_dir():
            for candidate in sorted(parent.glob("cuda*/bin/nvcc")):
                candidates.append(str(candidate))

    prefixes = [Path(sys.prefix), Path.home() / ".local"]
    for prefix in prefixes:
        for base in (
            prefix / "lib" / ("python%d.%d" % (sys.version_info.major, sys.version_info.minor)) / "site-packages",
            prefix / "Lib" / "site-packages",
        ):
            candidates.extend([
                str(base / "nvidia" / "cuda_nvcc" / "bin" / "nvcc"),
                str(base / "nvidia" / "cuda_nvcc" / "bin" / "nvcc.exe"),
            ])

    seen = set()
    for candidate in candidates:
        if not candidate or candidate in seen:
            continue
        seen.add(candidate)
        path = Path(candidate).expanduser()
        if path.is_file() and os.access(str(path), os.X_OK):
            return str(path.resolve())
    return None


def nvcc_info(requested=None):
    path = find_nvcc(requested)
    if path is None:
        return {"path": None, "available": False, "major": None, "version_text": None}
    code, text = _run([path, "--version"])
    major = None
    marker = "release "
    if code == 0 and marker in text:
        token = text.split(marker, 1)[1].split(",", 1)[0].strip()
        try:
            major = int(token.split(".", 1)[0])
        except Exception:
            major = None
    return {
        "path": path,
        "available": code == 0,
        "major": major,
        "version_text": text,
    }


def nvidia_smi_info():
    path = shutil.which("nvidia-smi")
    if path is None:
        return {"path": None, "available": False, "gpus": None, "error": "not on PATH"}
    code, text = _run([
        path,
        "--query-gpu=index,name,memory.total,driver_version",
        "--format=csv,noheader",
    ])
    return {
        "path": path,
        "available": code == 0,
        "gpus": text if code == 0 else None,
        "error": None if code == 0 else text,
    }


def backend_needs_build(expected_arch=DEFAULT_ARCH):
    ok, _ = backend_is_current(expected_arch=expected_arch)
    return not ok


def probe(expected_arch=DEFAULT_ARCH):
    compiler = nvcc_info()
    smi = nvidia_smi_info()
    current, reason = backend_is_current(expected_arch=expected_arch)
    metadata = load_build_metadata()
    return {
        "cuda_driver_library": ctypes.util.find_library("cuda"),
        "backend_library": str(CUDA_LIBRARY),
        "backend_exists": backend_exists(),
        "backend_current": current,
        "backend_reason": reason,
        "backend_metadata": metadata,
        "source_sha256": sha256_file(CUDA_SOURCE),
        "nvcc": compiler,
        "nvidia_smi": smi,
    }


def main():
    parser = argparse.ArgumentParser(description="Show SireSoft-IKON CUDA runtime/build status.")
    parser.add_argument("--arch", default=DEFAULT_ARCH)
    args = parser.parse_args()

    status = probe(args.arch)
    print("SireSoft-IKON CUDA status")
    print("runtime library:", status["backend_library"])
    print("precompiled backend:", "yes" if status["backend_exists"] else "no")
    print("backend current:", "yes" if status["backend_current"] else "no")
    print("backend check:", status["backend_reason"])

    metadata = status.get("backend_metadata") or {}
    if metadata:
        print("built architecture:", metadata.get("architecture") or "unknown")
        print("build toolkit:", metadata.get("cuda_toolkit") or "unknown")
        print("build target:", metadata.get("target") or "unknown")

    smi = status["nvidia_smi"]
    print("nvidia-smi:", "available" if smi.get("available") else "unavailable")
    if smi.get("gpus"):
        print("GPU(s):")
        print(smi["gpus"])

    compiler = status["nvcc"]
    print("nvcc (build-only):", compiler.get("path") or "not installed")
    print()
    print("Runtime rule: the server does not compile CUDA code.")
    print("Build rule: compile in GitHub Actions or on a Linux x86_64 machine with CUDA 12.x.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
