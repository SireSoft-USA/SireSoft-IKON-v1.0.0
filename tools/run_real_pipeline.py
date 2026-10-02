import argparse
import subprocess
import sys
from pathlib import Path

from real_runtime import ROOT, enter_project_root


# ============================================================
# TinyStories rebuild settings
# ============================================================

TINYSTORIES_PARTS_DIR = (
    ROOT
    / "datasets"
    / "canonical"
    / "tinystories_parts"
)

TINYSTORIES_OUTPUT = (
    ROOT
    / "datasets"
    / "canonical"
    / "tinystories.jsonl"
)

TINYSTORIES_PART_PATTERN = "tinystories.jsonl.part*"

BUFFER_SIZE = 16 * 1024 * 1024  # 16 MB


def human_size(size_bytes):
    size = float(size_bytes)

    for unit in (
        "B",
        "KB",
        "MB",
        "GB",
        "TB",
    ):
        if (
            size < 1024
            or unit == "TB"
        ):
            return f"{size:.2f} {unit}"

        size /= 1024

    return f"{size_bytes} B"


def rebuild_tinystories_if_needed():
    """
    Rebuild TinyStories from split Git LFS parts only if needed.

    If datasets/canonical/tinystories.jsonl already exists
    and is non-empty, reconstruction is skipped.
    """

    print()
    print("=" * 72)
    print("TinyStories dataset check")
    print("=" * 72)

    # --------------------------------------------------------
    # Already rebuilt -> skip
    # --------------------------------------------------------

    if (
        TINYSTORIES_OUTPUT.is_file()
        and TINYSTORIES_OUTPUT.stat().st_size > 0
    ):
        print(
            "[SKIP] TinyStories canonical dataset "
            "already exists."
        )

        print(
            "File:",
            TINYSTORIES_OUTPUT,
        )

        print(
            "Size:",
            human_size(
                TINYSTORIES_OUTPUT.stat().st_size
            ),
        )

        return

    # --------------------------------------------------------
    # Locate split files
    # --------------------------------------------------------

    parts = sorted(
        TINYSTORIES_PARTS_DIR.glob(
            TINYSTORIES_PART_PATTERN
        )
    )

    # --------------------------------------------------------
    # No split files available
    # --------------------------------------------------------

    if not parts:
        print(
            "[SKIP] No TinyStories split parts found."
        )

        print(
            "Preprocessing will attempt to create "
            "the canonical TinyStories dataset "
            "from the raw source."
        )

        return

    # --------------------------------------------------------
    # Rebuild required
    # --------------------------------------------------------

    expected_size = sum(
        part.stat().st_size
        for part in parts
    )

    print(
        "[REBUILD] TinyStories canonical dataset "
        "is missing."
    )

    print(
        "Parts found:",
        len(parts),
    )

    print(
        "Expected output size:",
        human_size(
            expected_size
        ),
    )

    TINYSTORIES_OUTPUT.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    temp_output = (
        TINYSTORIES_OUTPUT.with_suffix(
            TINYSTORIES_OUTPUT.suffix
            + ".rebuilding"
        )
    )

    if temp_output.exists():
        temp_output.unlink()

    try:
        with temp_output.open(
            "wb"
        ) as destination:

            for index, part in enumerate(
                parts,
                start=1,
            ):
                print(
                    "[MERGE]",
                    f"{index}/{len(parts)}",
                    part.name,
                    "-",
                    human_size(
                        part.stat().st_size
                    ),
                )

                with part.open(
                    "rb"
                ) as source:

                    while True:
                        chunk = source.read(
                            BUFFER_SIZE
                        )

                        if not chunk:
                            break

                        destination.write(
                            chunk
                        )

        # ----------------------------------------------------
        # Verify final size
        # ----------------------------------------------------

        rebuilt_size = (
            temp_output.stat().st_size
        )

        if rebuilt_size != expected_size:
            raise RuntimeError(
                "TinyStories reconstruction failed.\n"
                f"Expected: {expected_size} bytes\n"
                f"Created:  {rebuilt_size} bytes"
            )

        if TINYSTORIES_OUTPUT.exists():
            TINYSTORIES_OUTPUT.unlink()

        temp_output.replace(
            TINYSTORIES_OUTPUT
        )

        print()
        print(
            "[DONE] TinyStories reconstruction complete."
        )

        print(
            "Created:",
            TINYSTORIES_OUTPUT,
        )

        print(
            "Size:",
            human_size(
                TINYSTORIES_OUTPUT.stat().st_size
            ),
        )

    except Exception:
        if temp_output.exists():
            temp_output.unlink()

        raise


def run(command):
    print()
    print("=" * 72)
    print(
        "RUN:",
        " ".join(command),
    )
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
            "Run the actual SireSoft-IKON-v1.0 build pipeline: "
            "TinyStories rebuild -> preprocessing -> "
            "tokenizer -> model -> retrieval."
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

    tools = (
        ROOT
        / "tools"
    )

    # ========================================================
    # STEP 1 — TinyStories rebuild/check
    # ========================================================

    rebuild_tinystories_if_needed()

    # ========================================================
    # STEP 2 — Preprocessing
    # ========================================================

    if not args.skip_preprocessing:

        run([
            python,
            str(
                tools
                / "preprocess_all.py"
            ),
        ])

    else:

        print()
        print(
            "[SKIP] Preprocessing skipped by "
            "--skip-preprocessing"
        )

    # ========================================================
    # STEP 3 — Tokenizer training
    # ========================================================

    run([
        python,
        str(
            tools
            / "train_tokenizer.py"
        ),
        "--records-per-dataset",
        str(
            args.tokenizer_records_per_dataset
        ),
    ])

    # ========================================================
    # STEP 4 — Model training
    # ========================================================

    run([
        python,
        str(
            tools
            / "train_model.py"
        ),
        "--records-per-dataset",
        str(
            args.records_per_dataset
        ),
        "--epochs",
        str(
            args.epochs
        ),
        "--batch-size",
        str(
            args.batch_size
        ),
        "--sequence-length",
        str(
            args.sequence_length
        ),
    ])

    # ========================================================
    # STEP 5 — Retrieval index
    # ========================================================

    run([
        python,
        str(
            tools
            / "build_retrieval.py"
        ),
    ])

    print()
    print("=" * 72)
    print(
        "REAL SireSoft-IKON-v1.0 ARTIFACT BUILD COMPLETE"
    )
    print("=" * 72)

    print(
        "Tokenizer: "
        "model_store/manifests/"
        "sirellm_tokenizer.sltok"
    )

    print(
        "Model: "
        "model_store/checkpoints/"
        "sirellm-v1.lbckpt"
    )

    print(
        "Retrieval: "
        "vector_store/indexes/"
        "siresoft.slretr"
    )

    print()

    print(
        "Start RAG chat with:"
    )

    print(
        "  python tools/chat_rag.py"
    )


if __name__ == "__main__":
    main()