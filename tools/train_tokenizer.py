import argparse
import json
from pathlib import Path

from real_runtime import (
    ROOT,
    enter_project_root,
    load_tokenizer_namespace,
)


DEFAULT_DATASETS = (
    "dailydialog",
    "dolly",
    "movie-corpus",
    "siresoft",
    "tinystories",
    "openassistant",
)


def training_text(row):
    value = row.get("normalized_content")
    if isinstance(value, str) and value.strip():
        return value

    conversation = row.get("conversation")
    if isinstance(conversation, dict):
        messages = conversation.get("messages")
        if isinstance(messages, list):
            pieces = []
            for message in messages:
                if not isinstance(message, dict):
                    continue
                role = message.get("role")
                content = message.get("content")
                if isinstance(content, str) and content:
                    if isinstance(role, str) and role:
                        pieces.append(
                            "<" + role.upper() + ">"
                        )
                    pieces.append(content)
            if pieces:
                return "\n".join(pieces)

    value = row.get("raw_content")
    if isinstance(value, str) and value.strip():
        return value

    return ""


def read_corpus(
    datasets,
    records_per_dataset,
):
    corpus = []
    counts = {}

    for dataset_id in datasets:
        path = (
            ROOT
            / "datasets"
            / "canonical"
            / (dataset_id + ".jsonl")
        )

        if not path.is_file():
            raise FileNotFoundError(
                "Missing canonical dataset: "
                + str(path)
                + "\nRun: python tools/preprocess_all.py"
            )

        count = 0

        with path.open(
            "r",
            encoding="utf-8",
        ) as handle:
            for line in handle:
                line = line.strip()
                if not line:
                    continue

                row = json.loads(line)
                metadata = row.get("metadata")

                if (
                    isinstance(metadata, dict)
                    and metadata.get(
                        "training_eligible",
                        True,
                    ) is False
                ):
                    continue

                text = training_text(row)

                if not text:
                    continue

                corpus.append(text)
                count += 1

                if (
                    records_per_dataset > 0
                    and count
                    >= records_per_dataset
                ):
                    break

        counts[dataset_id] = count

    return corpus, counts


def main():
    parser = argparse.ArgumentParser(
        description=(
            "Train SireSoft-IKON-v1.0's real byte-level BPE tokenizer on canonical data."
        )
    )
    parser.add_argument(
        "--datasets",
        nargs="*",
        default=list(DEFAULT_DATASETS),
        choices=DEFAULT_DATASETS,
    )
    parser.add_argument(
        "--records-per-dataset",
        type=int,
        default=2000,
        help=(
            "Real records per dataset used to train the tokenizer. "
            "Use 0 for every canonical record."
        ),
    )
    parser.add_argument(
        "--vocab-size",
        type=int,
        default=512,
    )
    parser.add_argument(
        "--min-frequency",
        type=int,
        default=2,
    )
    parser.add_argument(
        "--output",
        default=(
            "model_store/manifests/"
            "sirellm_tokenizer.sltok"
        ),
    )
    args = parser.parse_args()

    if args.records_per_dataset < 0:
        raise ValueError(
            "--records-per-dataset must be >= 0"
        )

    enter_project_root()

    corpus, counts = read_corpus(
        args.datasets,
        args.records_per_dataset,
    )

    if not corpus:
        raise RuntimeError(
            "No canonical training text was found."
        )

    print("SireSoft-IKON-v1.0 tokenizer training")
    print("texts:", len(corpus))
    for key in args.datasets:
        print("  ", key, counts.get(key, 0))
    print("target vocab:", args.vocab_size)
    print()

    ns = load_tokenizer_namespace()
    manager = ns[
        "build_tokenizer_manager"
    ]()

    info = manager.train(
        corpus,
        vocab_size=args.vocab_size,
        min_frequency=args.min_frequency,
    )

    output_path = ROOT / args.output
    output_path.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    saved = manager.save_state_file(
        str(output_path)
    )

    print("TOKENIZER TRAINING COMPLETE")
    print("vocabulary size:", info["vocabulary_size"])
    print("merge count:", info["merge_count"])
    print("special tokens:", info["special_token_count"])
    print("artifact:", output_path)
    print("save info:", saved)


if __name__ == "__main__":
    main()
