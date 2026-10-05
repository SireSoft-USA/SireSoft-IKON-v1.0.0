"""CUDA environment discovery for SireSoft-IKON.

This module is intentionally standard-library only.  It distinguishes three
separate things that were previously conflated:

1. NVIDIA driver / GPU visibility (nvidia-smi, optional diagnostic)
2. the already-built SireSoft-IKON CUDA shared library (runtime requirement)
3. nvcc (build-time requirement only)

A machine does not need nvcc to *run* an already-built CUDA backend.
"""

import ctypes.util
import os
import shutil
import subprocess
import sys
from pathlib import Path

from real_runtime import ROOT


CUDA_LIBRARY = ROOT / "libs" / "core" / "gpu" / "libsireikon_cuda.so"
CUDA_SOURCE = ROOT / "libs" / "core" / "gpu" / "sireikon_cuda.cu"


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


def find_nvcc(requested=None):
    """Find nvcc on PATH or in common CUDA / NVIDIA Python-package locations."""
    candidates = []
    if requested:
        candidates.append(str(requested))
    env_nvcc = os.getenv("NVCC")
    if env_nvcc:
        candidates.append(env_nvcc)

    for name in ("nvcc",):
        resolved = shutil.which(name)
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


def backend_needs_build():
    if not CUDA_LIBRARY.is_file() or CUDA_LIBRARY.stat().st_size == 0:
        return True
    if CUDA_SOURCE.is_file() and CUDA_SOURCE.stat().st_mtime > CUDA_LIBRARY.stat().st_mtime:
        return True
    return False


def probe():
    compiler = nvcc_info()
    smi = nvidia_smi_info()
    return {
        "cuda_driver_library": ctypes.util.find_library("cuda"),
        "backend_library": str(CUDA_LIBRARY),
        "backend_exists": CUDA_LIBRARY.is_file() and CUDA_LIBRARY.stat().st_size > 0,
        "backend_needs_build": backend_needs_build(),
        "nvcc": compiler,
        "nvidia_smi": smi,
    }
