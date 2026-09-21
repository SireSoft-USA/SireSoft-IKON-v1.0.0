import argparse
import json
from pathlib import Path

from real_runtime import (
    ROOT,
    enter_project_root,
    load_tokenizer_namespace,
    load_training_namespace,
)


DEFAULT_DATASETS = (
    "dailydialog",
    "dolly",
    "movie-corpus",
    "siresoft",
    "tinystories",
    "openassistant",
)


def row_text(row):
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


def windows(token_ids, sequence_length):
    output = []
    width = sequence_length + 1
    start = 0

    while start < len(token_ids) - 1:
        piece = token_ids[
            start:start + width
        ]

        if len(piece) >= 2:
            output.append(piece)

        if len(piece) < width:
            break

        start += sequence_length

    return output


def make_batches(sequences, batch_size):
    return [
        sequences[index:index + batch_size]
        for index in range(
            0,
            len(sequences),
            batch_size,
        )
    ]


def load_sequences(
    tokenizer_manager,
    dataset_ids,
    records_per_dataset,
    sequence_length,
    validation_every,
):
    train = []
    validation = []
    counts = {}

    for dataset_id in dataset_ids:
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

        accepted = 0
        sequence_count = 0

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

                text = row_text(row)
                if not text:
                    continue

                token_ids = tokenizer_manager.encode(
                    text,
                    add_bos=True,
                    add_eos=True,
                )

                pieces = windows(
                    token_ids,
                    sequence_length,
                )

                if not pieces:
                    continue

                is_validation = (
                    (accepted + 1)
                    % validation_every
                    == 0
                )

                if is_validation:
                    validation.extend(pieces)
                else:
                    train.extend(pieces)

                accepted += 1
                sequence_count += len(pieces)

                if (
                    records_per_dataset > 0
                    and accepted
                    >= records_per_dataset
                ):
                    break

        counts[dataset_id] = {
            "records": accepted,
            "sequences": sequence_count,
        }

    return train, validation, counts


def main():
    parser = argparse.ArgumentParser(
        description=(
            "Train the real SireLLM decoder-only language model and write checkpoints."
        )
    )
    parser.add_argument(
        "--datasets",
        nargs="*",
        default=list(DEFAULT_DATASETS),
        choices=DEFAULT_DATASETS,
    )
    parser.add_argument(
        "--tokenizer",
        default=(
            "model_store/manifests/"
            "sirellm_tokenizer.sltok"
        ),
    )
    parser.add_argument(
        "--records-per-dataset",
        type=int,
        default=250,
        help=(
            "Real canonical records per dataset. "
            "Use 0 for all records."
        ),
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
        "--d-model",
        type=int,
        default=32,
    )
    parser.add_argument(
        "--layers",
        type=int,
        default=2,
    )
    parser.add_argument(
        "--heads",
        type=int,
        default=4,
    )
    parser.add_argument(
        "--d-ff",
        type=int,
        default=128,
    )
    parser.add_argument(
        "--learning-rate",
        type=float,
        default=0.001,
    )
    parser.add_argument(
        "--validation-every",
        type=int,
        default=20,
        help=(
            "Every Nth accepted source record becomes validation data."
        ),
    )
    parser.add_argument(
        "--seed",
        type=int,
        default=1337,
    )
    parser.add_argument(
        "--resume",
        default=None,
        help="Optional existing .lbckpt to resume from.",
    )
    parser.add_argument(
        "--output",
        default=(
            "model_store/checkpoints/"
            "sirellm-v1.lbckpt"
        ),
    )
    args = parser.parse_args()

    if args.records_per_dataset < 0:
        raise ValueError(
            "--records-per-dataset must be >= 0"
        )

    if args.epochs <= 0:
        raise ValueError("--epochs must be > 0")

    if args.batch_size <= 0:
        raise ValueError(
            "--batch-size must be > 0"
        )

    if args.sequence_length <= 1:
        raise ValueError(
            "--sequence-length must be > 1"
        )

    if args.d_model % args.heads != 0:
        raise ValueError(
            "--d-model must be divisible by --heads"
        )

    enter_project_root()

    token_ns = load_tokenizer_namespace()
    tokenizer_manager = token_ns[
        "build_tokenizer_manager"
    ]()

    tokenizer_path = ROOT / args.tokenizer
    tokenizer_manager.load_state_file(
        str(tokenizer_path)
    )

    tokenizer_info = tokenizer_manager.info()
    vocabulary = tokenizer_manager.model.vocabulary

    pad_id = vocabulary.special_id(
        "<PAD>"
    )

    train_sequences, validation_sequences, counts = (
        load_sequences(
            tokenizer_manager,
            args.datasets,
            args.records_per_dataset,
            args.sequence_length,
            args.validation_every,
        )
    )

    if not train_sequences:
        raise RuntimeError(
            "No trainable token sequences were produced."
        )

    if not validation_sequences:
        validation_sequences = train_sequences[:1]

    train_batches = make_batches(
        train_sequences,
        args.batch_size,
    )
    validation_batches = make_batches(
        validation_sequences,
        args.batch_size,
    )

    total_steps = max(
        1,
        len(train_batches)
        * args.epochs,
    )

    warmup_steps = min(
        100,
        max(
            1,
            total_steps // 20,
        ),
    )

    config = {
        "model": {
            "vocab_size": tokenizer_info[
                "vocabulary_size"
            ],
            "d_model": args.d_model,
            "num_layers": args.layers,
            "num_heads": args.heads,
            "d_ff": args.d_ff,
            "max_seq_len": args.sequence_length,
            "dropout": 0.0,
            "position_mode": "rotary",
            "padding_idx": pad_id,
            "seed": args.seed,
        },
        "optimizer": {
            "type": "adamw",
            "learning_rate": args.learning_rate,
            "weight_decay": 0.01,
        },
        "scheduler": {
            "type": "warmup_cosine",
            "max_learning_rate": args.learning_rate,
            "min_learning_rate": (
                args.learning_rate * 0.1
            ),
            "warmup_steps": warmup_steps,
            "decay_steps": total_steps,
            "start_learning_rate": (
                args.learning_rate * 0.1
            ),
        },
        "training": {
            "pad_token_id": pad_id,
            "ignore_index": -100,
            "max_sequence_length": (
                args.sequence_length
            ),
            "gradient_clip_norm": 1.0,
        },
    }

    train_ns = load_training_namespace()
    manager = train_ns[
        "TrainingJobManager"
    ]()

    job_id = "sirellm-v1"
    job = manager.create_job(
        job_id,
        config,
    )

    if args.resume:
        manager.load_checkpoint(
            job_id,
            str(ROOT / args.resume),
        )

    output_path = ROOT / args.output
    output_path.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    print("SireLLM REAL MODEL TRAINING")
    print("vocab size:", tokenizer_info["vocabulary_size"])
    print("parameters:", job.model.parameter_count())
    print("train sequences:", len(train_sequences))
    print("validation sequences:", len(validation_sequences))
    print("train batches:", len(train_batches))
    print("epochs:", args.epochs)
    print("model:", args.layers, "layers /", args.d_model, "d_model /", args.heads, "heads")
    print()

    for dataset_id in args.datasets:
        data = counts.get(dataset_id, {})
        print(
            "dataset",
            dataset_id,
            "records=",
            data.get("records", 0),
            "sequences=",
            data.get("sequences", 0),
        )

    print()

    for epoch_index in range(args.epochs):
        epoch_number = epoch_index + 1
        print(
            "[EPOCH",
            str(epoch_number) + "/" + str(args.epochs) + "]",
            "training",
            len(train_batches),
            "batches...",
            flush=True,
        )

        train_metrics = manager.train_epoch(
            job_id,
            train_batches,
        )

        validation_metrics = manager.evaluate(
            job_id,
            validation_batches,
        )

        epoch_path = output_path.with_name(
            output_path.stem
            + "-epoch-"
            + str(epoch_number).zfill(3)
            + output_path.suffix
        )

        metadata = {
            "dataset_ids": list(args.datasets),
            "records_per_dataset": (
                args.records_per_dataset
            ),
            "train_sequence_count": len(
                train_sequences
            ),
            "validation_sequence_count": len(
                validation_sequences
            ),
            "tokenizer_path": str(
                tokenizer_path
            ),
            "epoch_requested": epoch_number,
        }

        manager.save_checkpoint(
            job_id,
            str(epoch_path),
            metadata=metadata,
        )

        manager.save_checkpoint(
            job_id,
            str(output_path),
            metadata=metadata,
        )

        print(
            "[EPOCH",
            str(epoch_number) + "]",
            "train_loss=",
            train_metrics["loss"],
            "val_loss=",
            validation_metrics["loss"],
            "global_step=",
            train_metrics["global_step"],
            "lr=",
            train_metrics["learning_rate"],
        )
        print("checkpoint:", epoch_path)
        print("latest:", output_path)
        print()

    manager.complete(job_id)

    print("MODEL TRAINING COMPLETE")
    print("final checkpoint:", output_path)


if __name__ == "__main__":
    main()
