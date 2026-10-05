"""Verify that SireSoft-IKON can execute a real training step on CUDA.

This is both a manual GPU diagnostic and part of the project test surface.  A
machine without NVIDIA tooling is reported as SKIPPED by default instead of
failing the whole code test suite.  Pass --require-cuda when CUDA availability
must be treated as mandatory (the strict training pipeline uses that mode).
"""

import argparse
import math
import subprocess
import sys

from real_runtime import ROOT, enter_project_root, load_training_namespace
from cuda_status import CUDA_LIBRARY, backend_needs_build, nvidia_smi_info, nvcc_info


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


def skip_or_fail(message, required):
    if required:
        raise RuntimeError(message)
    print("GPU TRAINING TEST: SKIPPED")
    print(message)
    print("Use --require-cuda to make missing CUDA support a test failure.")
    return False


def show_nvidia_smi():
    info = nvidia_smi_info()
    if info.get("available"):
        print("NVIDIA GPUs visible to the operating system:")
        print(info.get("gpus") or "(no rows returned)")
        print()
    else:
        print("[INFO] nvidia-smi diagnostic unavailable:", info.get("error"))
        print("The backend itself will still be tested if it can load CUDA.")
        print()


def maybe_build_backend(build_if_needed, arch, required):
    if not backend_needs_build():
        print("CUDA backend already built:", CUDA_LIBRARY)
        return True

    if not build_if_needed:
        return skip_or_fail(
            "CUDA backend is not built. Re-run with --build-if-needed, or provide "
            "a prebuilt libsireikon_cuda.so.",
            required,
        )

    compiler = nvcc_info()
    if not compiler.get("available") and not CUDA_LIBRARY.is_file():
        return skip_or_fail(
            "CUDA backend needs a build, but no CUDA compiler is available. "
            "This is a build-time limitation, not a Python/runtime CUDA error.",
            required,
        )

    print("Preparing CUDA backend before test...")
    command = [
        sys.executable,
        str(ROOT / "tools" / "build_cuda_backend.py"),
        "--arch",
        arch,
    ]
    if required:
        command.append("--required")
    completed = subprocess.run(command, cwd=ROOT)
    if completed.returncode != 0:
        return skip_or_fail("CUDA backend build failed", required)
    if not CUDA_LIBRARY.is_file() or CUDA_LIBRARY.stat().st_size == 0:
        return skip_or_fail("CUDA backend is still unavailable after build step", required)
    print()
    return True


def show_compute_processes():
    info = nvidia_smi_info()
    path = info.get("path")
    if not path:
        return
    completed = subprocess.run(
        [
            path,
            "--query-compute-apps=pid,process_name,used_gpu_memory",
            "--format=csv,noheader",
        ],
        cwd=ROOT,
        capture_output=True,
        text=True,
    )
    if completed.returncode == 0:
        output = (completed.stdout or "").strip()
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
    parser.add_argument(
        "--require-cuda",
        action="store_true",
        help="Fail instead of SKIP when CUDA cannot be activated.",
    )
    args = parser.parse_args()

    if args.steps <= 0:
        raise ValueError("--steps must be > 0")

    enter_project_root()

    print("=" * 72)
    print("SireSoft-IKON CUDA TRAINING TEST")
    print("=" * 72)

    show_nvidia_smi()
    if not maybe_build_backend(args.build_if_needed, args.arch, args.require_cuda):
        return 0

    ns = load_training_namespace()
    backend = ns["GPU_BACKEND"]
    try:
        status = backend.configure(
            "cuda",
            args.cuda_device_index,
            strict=True,
        )
    except Exception as error:
        if args.require_cuda:
            raise
        print("GPU TRAINING TEST: SKIPPED")
        print("CUDA backend could not be activated:", error)
        return 0

    backend.reset_call_stats()

    if status.get("active") != "cuda":
        skip_or_fail("CUDA backend did not become active", args.require_cuda)
        return 0

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
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
