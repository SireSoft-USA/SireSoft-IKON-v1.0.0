from __future__ import annotations

import argparse
from pathlib import Path

DEFAULT_PARTS_DIR = Path("datasets/canonical/tinystories_parts")
DEFAULT_OUTPUT = Path("datasets/canonical/tinystories.jsonl")
PART_PATTERN = "tinystories.jsonl.part*"
BUFFER_SIZE = 16 * 1024 * 1024


def human_size(size_bytes: int) -> str:
    size = float(size_bytes)
    for unit in ("B", "KB", "MB", "GB", "TB"):
        if size < 1024 or unit == "TB":
            return f"{size:.2f} {unit}"
        size /= 1024
    return f"{size_bytes} B"


def rebuild(parts_dir: Path, output: Path, force: bool = False) -> None:
    parts = sorted(parts_dir.glob(PART_PATTERN))

    if not parts:
        raise FileNotFoundError(
            f"No TinyStories parts found in: {parts_dir}\n"
            f"Expected files matching: {PART_PATTERN}\n"
            "If this is a fresh clone, run `git lfs pull` first."
        )

    if output.exists() and not force:
        print("[SireLLM] TinyStories canonical file already exists:")
        print(f"  {output}")
        print(f"  Size: {human_size(output.stat().st_size)}")
        print("[SireLLM] Nothing to rebuild.")
        print("[SireLLM] Use --force only if you intentionally want to rebuild it.")
        return

    expected_size = sum(part.stat().st_size for part in parts)

    print("[SireLLM] Rebuilding canonical TinyStories dataset")
    print(f"[SireLLM] Parts found: {len(parts)}")
    print(f"[SireLLM] Expected output size: {human_size(expected_size)}")

    output.parent.mkdir(parents=True, exist_ok=True)
    temp_output = output.with_suffix(output.suffix + ".rebuilding")

    if temp_output.exists():
        temp_output.unlink()

    try:
        with temp_output.open("wb") as destination:
            for index, part in enumerate(parts, start=1):
                part_size = part.stat().st_size
                print(
                    f"[SireLLM] Merging {index}/{len(parts)}: "
                    f"{part.name} ({human_size(part_size)})"
                )

                with part.open("rb") as source:
                    while True:
                        chunk = source.read(BUFFER_SIZE)
                        if not chunk:
                            break
                        destination.write(chunk)

        rebuilt_size = temp_output.stat().st_size

        if rebuilt_size != expected_size:
            raise RuntimeError(
                "Rebuilt TinyStories size mismatch.\n"
                f"Expected: {expected_size} bytes\n"
                f"Created:  {rebuilt_size} bytes"
            )

        if output.exists():
            output.unlink()

        temp_output.replace(output)

        print()
        print("[SireLLM] TinyStories reconstruction complete.")
        print(f"[SireLLM] Created: {output}")
        print(f"[SireLLM] Final size: {human_size(output.stat().st_size)}")
        print("[SireLLM] Dataset is ready for preprocessing/training.")

    except Exception:
        if temp_output.exists():
            temp_output.unlink()
        raise


def main() -> None:
    parser = argparse.ArgumentParser(
        description=(
            "Rebuild datasets/canonical/tinystories.jsonl from Git LFS split parts."
        )
    )
    parser.add_argument(
        "--parts-dir",
        type=Path,
        default=DEFAULT_PARTS_DIR,
        help=f"Directory containing split parts (default: {DEFAULT_PARTS_DIR})",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=DEFAULT_OUTPUT,
        help=f"Reconstructed output file (default: {DEFAULT_OUTPUT})",
    )
    parser.add_argument(
        "--force",
        action="store_true",
        help="Rebuild even if the output file already exists.",
    )

    args = parser.parse_args()

    rebuild(
        parts_dir=args.parts_dir,
        output=args.output,
        force=args.force,
    )


if __name__ == "__main__":
    main()
