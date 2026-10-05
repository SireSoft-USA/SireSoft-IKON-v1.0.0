"""One-command SireSoft-IKON training/deployment pipeline.

Production CUDA is runtime-only: this command NEVER invokes nvcc and NEVER
compiles native code on the GPU server.  The Linux ``libsireikon_cuda.so`` is
built ahead of time (normally by GitHub Actions) and committed with matching
source-hash metadata.  The default device is strict CUDA so production cannot
silently spend hours training on CPU.

Use ``--device cpu`` explicitly for laptop/development runs without NVIDIA GPU.
"""

import argparse
import subprocess
import sys
from pathlib import Path

from real_runtime import ROOT, enter_project_root
from cuda_status import CUDA_LIBRARY, backend_is_current, load_build_metadata, nvidia_smi_info


TINYSTORIES_PARTS_DIR = ROOT / "datasets" / "canonical" / "tinystories_parts"
TINYSTORIES_OUTPUT = ROOT / "datasets" / "canonical" / "tinystories.jsonl"
TINYSTORIES_PART_PATTERN = "tinystories.jsonl.part*"
BUFFER_SIZE = 16 * 1024 * 1024

CANONICAL_DATASETS = (
    "dailydialog",
    "dolly",
    "movie-corpus",
    "siresoft",
    "tinystories",
    "openassistant",
)


def human_size(size_bytes):
    size = float(size_bytes)
    for unit in ("B", "KB", "MB", "GB", "TB"):
        if size < 1024 or unit == "TB":
            return f"{size:.2f} {unit}"
        size /= 1024
    return f"{size_bytes} B"


def banner(text):
    print()
    print("=" * 72)
    print(text)
    print("=" * 72)


def run(command, required=True):
    print()
    print("RUN:", " ".join(str(item) for item in command))
    print("-" * 72)

    completed = subprocess.run(command, cwd=ROOT)
    if completed.returncode != 0 and required:
        raise SystemExit(completed.returncode)
    return completed.returncode


def rebuild_tinystories_if_needed():
    banner("STEP: TinyStories canonical dataset check/rebuild")

    if TINYSTORIES_OUTPUT.is_file() and TINYSTORIES_OUTPUT.stat().st_size > 0:
        print("[SKIP] TinyStories canonical dataset already exists.")
        print("file:", TINYSTORIES_OUTPUT)
        print("size:", human_size(TINYSTORIES_OUTPUT.stat().st_size))
        return

    parts = sorted(TINYSTORIES_PARTS_DIR.glob(TINYSTORIES_PART_PATTERN))
    if not parts:
        print("[SKIP] No split TinyStories parts found.")
        print("Preprocessing will attempt to use the raw TinyStories source.")
        return

    expected_size = sum(part.stat().st_size for part in parts)
    print("[REBUILD] parts:", len(parts))
    print("expected size:", human_size(expected_size))

    TINYSTORIES_OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    temporary = TINYSTORIES_OUTPUT.with_suffix(
        TINYSTORIES_OUTPUT.suffix + ".rebuilding"
    )
    if temporary.exists():
        temporary.unlink()

    try:
        with temporary.open("wb") as destination:
            for index, part in enumerate(parts, start=1):
                print(
                    f"[MERGE] {index}/{len(parts)} {part.name} "
                    f"({human_size(part.stat().st_size)})"
                )
                with part.open("rb") as source:
                    while True:
                        chunk = source.read(BUFFER_SIZE)
                        if not chunk:
                            break
                        destination.write(chunk)

        rebuilt_size = temporary.stat().st_size
        if rebuilt_size != expected_size:
            raise RuntimeError(
                "TinyStories reconstruction size mismatch: "
                f"expected {expected_size}, created {rebuilt_size}"
            )

        if TINYSTORIES_OUTPUT.exists():
            TINYSTORIES_OUTPUT.unlink()
        temporary.replace(TINYSTORIES_OUTPUT)
        print("[DONE]", TINYSTORIES_OUTPUT)
        print("size:", human_size(TINYSTORIES_OUTPUT.stat().st_size))

    except Exception:
        if temporary.exists():
            temporary.unlink()
        raise


def prepare_compute(args, python, tools):
    banner("STEP: Compute backend verification")

    if args.device == "cpu":
        print("CPU mode requested explicitly. CUDA runtime test skipped.")
        run([
            python,
            str(tools / "test_compute_backend.py"),
            "--device",
            "cpu",
        ])
        return

    current, reason = backend_is_current(expected_arch=args.cuda_arch)
    metadata = load_build_metadata() or {}
    smi = nvidia_smi_info()

    print("CUDA runtime backend:", CUDA_LIBRARY)
    print("precompiled backend:", "yes" if CUDA_LIBRARY.is_file() else "no")
    print("backend check:", reason)
    if metadata:
        print("backend architecture:", metadata.get("architecture") or "unknown")
        print("backend CUDA toolkit:", metadata.get("cuda_toolkit") or "unknown")
    print("NVIDIA driver/GPU visibility:", "yes" if smi.get("available") else "no")
    if smi.get("gpus"):
        print(smi["gpus"])

    if not current:
        if args.device == "cuda":
            raise SystemExit(
                "Strict CUDA training requires the precompiled backend, but "
                + reason
                + ". This server does not build CUDA code. Push the project to GitHub "
                  "and run the 'Build CUDA Backend (sm_61)' workflow, or compile on a "
                  "Linux x86_64 development machine with CUDA 12.x using "
                  "`python tools/build_cuda_backend.py --arch sm_61 --required`, then commit "
                  "libs/core/gpu/libsireikon_cuda.so and its .build.json metadata."
            )
        print("[INFO] Precompiled CUDA backend is unavailable/stale; auto mode will use CPU.")
        run([
            python,
            str(tools / "test_compute_backend.py"),
            "--device",
            "auto",
            "--cuda-device-index",
            str(args.cuda_device_index),
        ])
        return

    if args.skip_gpu_test:
        print("[SKIP] GPU smoke test skipped by --skip-gpu-test")
        return

    if args.device == "cuda":
        run([
            python,
            str(tools / "test_gpu_training.py"),
            "--cuda-device-index",
            str(args.cuda_device_index),
            "--arch",
            args.cuda_arch,
            "--require-cuda",
        ])
    else:
        run([
            python,
            str(tools / "test_compute_backend.py"),
            "--device",
            "auto",
            "--cuda-device-index",
            str(args.cuda_device_index),
        ])


def verify_canonical_datasets():
    missing = []
    print()
    print("Canonical dataset verification:")
    for dataset_id in CANONICAL_DATASETS:
        path = ROOT / "datasets" / "canonical" / (dataset_id + ".jsonl")
        if path.is_file() and path.stat().st_size > 0:
            print(" [OK]", dataset_id, human_size(path.stat().st_size))
        else:
            print(" [MISSING]", dataset_id)
            missing.append(str(path))

    if missing:
        raise SystemExit(
            "Canonical dataset build is incomplete. Missing:\n  "
            + "\n  ".join(missing)
        )


def verify_artifacts():
    expected = (
        ROOT / "model_store" / "manifests" / "sirellm_tokenizer.sltok",
        ROOT / "model_store" / "checkpoints" / "sirellm-v1.lbckpt",
        ROOT / "vector_store" / "indexes" / "siresoft.slretr",
    )

    banner("STEP: Final artifact verification")
    missing = []
    for path in expected:
        if path.is_file() and path.stat().st_size > 0:
            print("[OK]", path.relative_to(ROOT), human_size(path.stat().st_size))
        else:
            print("[MISSING]", path.relative_to(ROOT))
            missing.append(path)

    if missing:
        raise SystemExit("Pipeline finished with missing required artifacts.")


def main():
    parser = argparse.ArgumentParser(
        description=(
            "Run SireSoft-IKON end to end: compute preflight -> datasets -> "
            "preprocessing -> tokenizer -> resumable training -> retrieval."
        )
    )

    parser.add_argument("--records-per-dataset", type=int, default=250)
    parser.add_argument("--tokenizer-records-per-dataset", type=int, default=2000)
    parser.add_argument("--epochs", type=int, default=1)
    parser.add_argument("--batch-size", type=int, default=4)
    parser.add_argument("--sequence-length", type=int, default=64)

    parser.add_argument(
        "--device",
        choices=("cuda", "auto", "cpu"),
        default="cuda",
        help=(
            "Default is strict GPU-only CUDA deployment mode. Use --device cpu "
            "explicitly on a laptop without NVIDIA GPU, or auto only when CPU fallback "
            "is intentionally acceptable."
        ),
    )
    parser.add_argument("--cuda-device-index", type=int, default=0)
    parser.add_argument(
        "--cuda-arch",
        default="sm_61",
        help="Quadro P5000 is Pascal sm_61.",
    )

    parser.add_argument("--skip-gpu-test", action="store_true")
    parser.add_argument("--skip-preprocessing", action="store_true")
    parser.add_argument("--skip-tokenizer", action="store_true")
    parser.add_argument("--skip-retrieval", action="store_true")

    parser.add_argument(
        "--checkpoint-every",
        type=int,
        default=100,
        help="Save resumable model state every N batches.",
    )
    parser.add_argument(
        "--keep-step-checkpoints",
        type=int,
        default=5,
        help="Number of numbered step checkpoints retained.",
    )
    parser.add_argument(
        "--progress-every",
        type=int,
        default=1,
        help="Refresh live training visualization every N batches.",
    )
    parser.add_argument(
        "--fresh",
        action="store_true",
        help="Do not automatically resume an existing progress checkpoint.",
    )
    parser.add_argument(
        "--resume",
        default=None,
        help="Explicit checkpoint path for model training resume.",
    )
    parser.add_argument(
        "--start-app",
        action="store_true",
        help="Start app.py after all build artifacts are complete.",
    )

    args = parser.parse_args()

    enter_project_root()
    python = sys.executable
    tools = ROOT / "tools"

    banner("SireSoft-IKON-v1.0 ONE-COMMAND REAL PIPELINE")
    print("project:", ROOT)
    print("python:", python)
    print("training device:", args.device)
    print("CUDA device index:", args.cuda_device_index)
    print("CUDA architecture:", args.cuda_arch)
    print("checkpoint interval:", args.checkpoint_every, "batches")

    # 1. GPU/custom compute backend.
    prepare_compute(args, python, tools)

    # 2. Rebuild split canonical data when necessary.
    rebuild_tinystories_if_needed()

    # 3. Raw -> canonical preprocessing.
    banner("STEP: Dataset preprocessing")
    if args.skip_preprocessing:
        print("[SKIP] Preprocessing skipped by --skip-preprocessing")
    else:
        run([python, str(tools / "preprocess_all.py")])
    verify_canonical_datasets()

    # 4. Train tokenizer.
    banner("STEP: Tokenizer training")
    if args.skip_tokenizer:
        print("[SKIP] Tokenizer training skipped by --skip-tokenizer")
    else:
        run([
            python,
            str(tools / "train_tokenizer.py"),
            "--records-per-dataset",
            str(args.tokenizer_records_per_dataset),
        ])

    # 5. Train the real model with live progress + checkpoints.
    banner("STEP: Model training")
    train_command = [
        python,
        str(tools / "train_model.py"),
        "--records-per-dataset",
        str(args.records_per_dataset),
        "--epochs",
        str(args.epochs),
        "--batch-size",
        str(args.batch_size),
        "--sequence-length",
        str(args.sequence_length),
        "--device",
        args.device,
        "--cuda-device-index",
        str(args.cuda_device_index),
        "--checkpoint-every",
        str(args.checkpoint_every),
        "--keep-step-checkpoints",
        str(args.keep_step_checkpoints),
        "--progress-every",
        str(args.progress_every),
    ]

    if args.resume:
        train_command.extend(["--resume", args.resume])
    elif not args.fresh:
        train_command.append("--auto-resume")

    run(train_command)

    # 6. Build the SireSoft retrieval/RAG index.
    banner("STEP: Retrieval / RAG index")
    if args.skip_retrieval:
        print("[SKIP] Retrieval build skipped by --skip-retrieval")
    else:
        run([python, str(tools / "build_retrieval.py")])

    # 7. Verify all outputs.
    if not args.skip_retrieval:
        verify_artifacts()

    banner("SireSoft-IKON REAL PIPELINE COMPLETE")
    print("Tokenizer: model_store/manifests/sirellm_tokenizer.sltok")
    print("Model: model_store/checkpoints/sirellm-v1.lbckpt")
    print("Resume state: model_store/checkpoints/sirellm-v1-progress.lbckpt")
    print("Training metrics: model_store/checkpoints/sirellm-v1-training.jsonl")
    print("Retrieval: vector_store/indexes/siresoft.slretr")
    print()
    print("RAG CLI: python tools/chat_rag.py")
    print("GPU test: python tools/test_gpu_training.py --arch sm_61 --require-cuda")
    print("CUDA build (development/CI only): python tools/build_cuda_backend.py --arch sm_61 --required")

    if args.start_app:
        banner("STEP: Starting application")
        run([python, str(ROOT / "app.py")])


if __name__ == "__main__":
    main()
