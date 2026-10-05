"""Verify that SireSoft-IKON can execute a real training step on CUDA.

No datasets, tokenizer artifacts, PyTorch, TensorFlow, NumPy, CuPy or Numba are
required.  The test builds a tiny SireSoft-IKON Transformer in memory, performs
real forward/backward/AdamW steps, and verifies that the project's custom CUDA
kernels were actually called.

Typical server use:
    python tools/test_gpu_training.py --build-if-needed --arch sm_61
"""

import argparse
import math
import shutil
import subprocess
import sys
from pathlib import Path

from real_runtime import ROOT, enter_project_root, load_training_namespace


REQUIRED_KERNELS = (
    "matmul",
    "embedding_forward",
    "attention_forward",
    "attention_backward",
    "layernorm_forward",
    "layernorm_backward",
    "cross_entropy_forward",
    "cross_entropy_backward",
    "adamw",
)


def run_text(command):
    completed = subprocess.run(
        command,
        cwd=ROOT,
        capture_output=True,
        text=True,
    )
    text = (completed.stdout or "") + (completed.stderr or "")
    return completed.returncode, text.strip()


def ensure_nvidia_smi():
    executable = shutil.which("nvidia-smi")
    if executable is None:
        raise RuntimeError("nvidia-smi was not found on PATH")

    code, output = run_text([
        executable,
        "--query-gpu=index,name,memory.total",
        "--format=csv,noheader",
    ])
    if code != 0:
        raise RuntimeError("nvidia-smi failed:\n" + output)

    print("NVIDIA GPUs visible to the operating system:")
    print(output)
    print()


def maybe_build_backend(build_if_needed, arch):
    library = ROOT / "libs" / "core" / "gpu" / "libsireikon_cuda.so"
    source = ROOT / "libs" / "core" / "gpu" / "sireikon_cuda.cu"

    needs_build = not library.is_file()
    if library.is_file() and source.is_file():
        needs_build = source.stat().st_mtime > library.stat().st_mtime

    if not needs_build:
        print("CUDA backend already built:", library)
        return

    if not build_if_needed:
        raise RuntimeError(
            "CUDA backend is not built. Run:\n"
            f"  python tools/build_cuda_backend.py --arch {arch}\n"
            "or rerun this test with --build-if-needed."
        )

    print("Building CUDA backend before test...")
    completed = subprocess.run(
        [
            sys.executable,
            str(ROOT / "tools" / "build_cuda_backend.py"),
            "--arch",
            arch,
        ],
        cwd=ROOT,
    )
    if completed.returncode != 0:
        raise RuntimeError("CUDA backend build failed")
    print()


def show_compute_processes():
    executable = shutil.which("nvidia-smi")
    if executable is None:
        return

    code, output = run_text([
        executable,
        "--query-compute-apps=pid,process_name,used_gpu_memory",
        "--format=csv,noheader",
    ])
    if code == 0:
        print("GPU compute processes after training test:")
        print(output if output else "(none reported)")
        print()


def main():
    parser = argparse.ArgumentParser(
        description="Run a real SireSoft-IKON CUDA training smoke test."
    )
    parser.add_argument("--cuda-device-index", type=int, default=0)
    parser.add_argument("--steps", type=int, default=3)
    parser.add_argument("--arch", default="sm_61")
    parser.add_argument("--build-if-needed", action="store_true")
    args = parser.parse_args()

    if args.steps <= 0:
        raise ValueError("--steps must be > 0")

    enter_project_root()

    print("=" * 72)
    print("SireSoft-IKON CUDA TRAINING TEST")
    print("=" * 72)

    ensure_nvidia_smi()
    maybe_build_backend(args.build_if_needed, args.arch)

    ns = load_training_namespace()
    backend = ns["GPU_BACKEND"]
    status = backend.configure(
        "cuda",
        args.cuda_device_index,
        strict=True,
    )
    backend.reset_call_stats()

    if status.get("active") != "cuda":
        raise RuntimeError("CUDA backend did not become active")

    print("CUDA backend active")
    print("device index:", status.get("device_index"))
    print("library:", status.get("library"))
    print()

    TrainingJobManager = ns["TrainingJobManager"]

    config = {
        "model": {
            "vocab_size": 48,
            "d_model": 8,
            "num_layers": 1,
            "num_heads": 2,
            "d_ff": 16,
            "max_seq_len": 8,
            "dropout": 0.0,
            "position_mode": "rotary",
            "padding_idx": 0,
            "seed": 1337,
        },
        "optimizer": {
            "type": "adamw",
            "learning_rate": 0.001,
            "weight_decay": 0.01,
        },
        "scheduler": {
            "type": "constant",
            "learning_rate": 0.001,
        },
        "training": {
            "device": "cuda",
            "cuda_device_index": args.cuda_device_index,
            "pad_token_id": 0,
            "ignore_index": -100,
            "max_sequence_length": 8,
            "gradient_clip_norm": 1.0,
        },
    }

    manager = TrainingJobManager()
    manager.create_job("gpu-smoke", config)

    sequences = [
        [1, 2, 3, 4, 5, 6],
        [2, 3, 4, 5, 6, 7],
        [8, 9, 10, 11, 12, 13],
        [3, 5, 7, 9, 11, 13],
    ]

    losses = []
    for step in range(1, args.steps + 1):
        metrics = manager.train_step("gpu-smoke", sequences)
        loss = float(metrics["loss"])
        if not math.isfinite(loss):
            raise RuntimeError("non-finite training loss")
        losses.append(loss)
        print(
            f"step {step}/{args.steps} "
            f"loss={loss:.6f} "
            f"global_step={metrics['global_step']}"
        )

    final = backend.status()
    calls = final.get("calls", {})

    missing = [
        name
        for name in REQUIRED_KERNELS
        if int(calls.get(name, 0)) <= 0
    ]
    if missing:
        raise RuntimeError(
            "CUDA backend was selected but required kernels were not exercised: "
            + ", ".join(missing)
        )

    show_compute_processes()

    print("CUDA kernel call counts:")
    for name in sorted(calls):
        print(" ", name, "=", calls[name])
    print()
    print("=" * 72)
    print("GPU TRAINING TEST: PASS")
    print("SireSoft-IKON executed real model training through custom CUDA kernels.")
    print("losses:", ", ".join(f"{value:.6f}" for value in losses))
    print("=" * 72)


if __name__ == "__main__":
    main()
