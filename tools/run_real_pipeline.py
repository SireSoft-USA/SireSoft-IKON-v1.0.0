import argparse
import subprocess
import sys
from pathlib import Path

from real_runtime import ROOT, enter_project_root


def run(command):
    print()
    print("=" * 72)
    print("RUN:", " ".join(command))
    print("=" * 72)
    completed = subprocess.run(
        command,
        cwd=ROOT,
    )
    if completed.returncode != 0:
        raise SystemExit(
            completed.returncode
        )


def main():
    parser = argparse.ArgumentParser(
        description=(
            "Run the actual SireLLM build pipeline: preprocess -> tokenizer -> model -> retrieval."
        )
    )
    parser.add_argument(
        "--records-per-dataset",
        type=int,
        default=250,
        help=(
            "Real records per dataset for model training. "
            "Use 0 for all canonical records."
        ),
    )
    parser.add_argument(
        "--tokenizer-records-per-dataset",
        type=int,
        default=2000,
    )
    parser.add_argument(
        "--epochs",
        type=int,
        default=1,
    )
    parser.add_argument(
        "--batch-size",
        type=int,
        default=4,
    )
    parser.add_argument(
        "--sequence-length",
        type=int,
        default=64,
    )
    parser.add_argument(
        "--skip-preprocessing",
        action="store_true",
    )
    args = parser.parse_args()

    enter_project_root()
    python = sys.executable
    tools = ROOT / "tools"

    if not args.skip_preprocessing:
        run([
            python,
            str(tools / "preprocess_all.py"),
        ])

    run([
        python,
        str(tools / "train_tokenizer.py"),
        "--records-per-dataset",
        str(
            args.tokenizer_records_per_dataset
        ),
    ])

    run([
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
    ])

    run([
        python,
        str(tools / "build_retrieval.py"),
    ])

    print()
    print("REAL SireLLM ARTIFACT BUILD COMPLETE")
    print(
        "Tokenizer: model_store/manifests/sirellm_tokenizer.sltok"
    )
    print(
        "Model: model_store/checkpoints/sirellm-v1.lbckpt"
    )
    print(
        "Retrieval: vector_store/indexes/siresoft.slretr"
    )
    print()
    print("Start RAG chat with:")
    print("  python tools/chat_rag.py")


if __name__ == "__main__":
    main()
