import argparse
import json
import sys
import time
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
                        pieces.append("<" + role.upper() + ">")
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
        piece = token_ids[start:start + width]

        if len(piece) >= 2:
            output.append(piece)

        if len(piece) < width:
            break

        start += sequence_length

    return output


def make_batches(sequences, batch_size):
    return [
        sequences[index:index + batch_size]
        for index in range(0, len(sequences), batch_size)
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
        path = ROOT / "datasets" / "canonical" / (dataset_id + ".jsonl")

        if not path.is_file():
            raise FileNotFoundError(
                "Missing canonical dataset: "
                + str(path)
                + "\nRun: python tools/preprocess_all.py"
            )

        accepted = 0
        sequence_count = 0

        with path.open("r", encoding="utf-8") as handle:
            for line in handle:
                line = line.strip()
                if not line:
                    continue

                row = json.loads(line)
                metadata = row.get("metadata")

                if (
                    isinstance(metadata, dict)
                    and metadata.get("training_eligible", True) is False
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

                pieces = windows(token_ids, sequence_length)

                if not pieces:
                    continue

                is_validation = ((accepted + 1) % validation_every == 0)

                if is_validation:
                    validation.extend(pieces)
                else:
                    train.extend(pieces)

                accepted += 1
                sequence_count += len(pieces)

                if records_per_dataset > 0 and accepted >= records_per_dataset:
                    break

        counts[dataset_id] = {
            "records": accepted,
            "sequences": sequence_count,
        }

    return train, validation, counts


def format_duration(seconds):
    if seconds is None or seconds < 0:
        return "--:--:--"
    seconds = int(seconds)
    hours = seconds // 3600
    minutes = (seconds % 3600) // 60
    seconds = seconds % 60
    return f"{hours:02d}:{minutes:02d}:{seconds:02d}"


def progress_bar(current, total, width=30):
    if total <= 0:
        return "[" + ("-" * width) + "]"
    ratio = min(1.0, max(0.0, float(current) / float(total)))
    filled = int(ratio * width)
    return "[" + ("#" * filled) + ("-" * (width - filled)) + "]"


def write_metric(path, record):
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(record, sort_keys=True) + "\n")


def remove_old_step_checkpoints(output_path, keep):
    if keep <= 0:
        return

    pattern = output_path.stem + "-step-*" + output_path.suffix
    items = sorted(
        output_path.parent.glob(pattern),
        key=lambda path: path.stat().st_mtime,
    )

    while len(items) > keep:
        old = items.pop(0)
        try:
            old.unlink()
        except FileNotFoundError:
            pass


def common_metadata(
    args,
    tokenizer_path,
    train_sequences,
    validation_sequences,
    compute_status,
):
    return {
        "dataset_ids": list(args.datasets),
        "records_per_dataset": args.records_per_dataset,
        "train_sequence_count": len(train_sequences),
        "validation_sequence_count": len(validation_sequences),
        "tokenizer_path": str(tokenizer_path),
        "compute_device_requested": args.device,
        "compute_device_active": compute_status.get("active"),
        "cuda_device_index": args.cuda_device_index,
    }


def save_progress_checkpoint(
    manager,
    job_id,
    output_path,
    progress_path,
    args,
    tokenizer_path,
    train_sequences,
    validation_sequences,
    compute_status,
    epoch_index,
    next_batch_index,
    total_batches,
    weighted_loss,
    targets,
    batches_completed,
    latest_loss,
):
    metadata = common_metadata(
        args,
        tokenizer_path,
        train_sequences,
        validation_sequences,
        compute_status,
    )
    metadata.update({
        "checkpoint_kind": "in_epoch",
        "resume_epoch_index": int(epoch_index),
        "next_batch_index": int(next_batch_index),
        "total_batches_per_epoch": int(total_batches),
        "epoch_weighted_loss": float(weighted_loss),
        "epoch_targets": int(targets),
        "epoch_batches_completed": int(batches_completed),
        "latest_batch_loss": float(latest_loss),
    })

    step_path = output_path.with_name(
        output_path.stem
        + "-step-"
        + str(manager.get(job_id).trainer.state.global_step).zfill(9)
        + output_path.suffix
    )

    manager.save_checkpoint(job_id, str(step_path), metadata=metadata)
    manager.save_checkpoint(job_id, str(progress_path), metadata=metadata)
    remove_old_step_checkpoints(output_path, args.keep_step_checkpoints)

    return step_path


def train_epoch_live(
    manager,
    job_id,
    sequence_batches,
    epoch_index,
    epochs,
    start_batch_index,
    output_path,
    progress_path,
    metrics_path,
    args,
    tokenizer_path,
    train_sequences,
    validation_sequences,
    compute_status,
    resume_weighted_loss=0.0,
    resume_targets=0,
    resume_batches_completed=0,
):
    job = manager.get(job_id)
    total_batches = len(sequence_batches)

    if start_batch_index < 0 or start_batch_index > total_batches:
        raise ValueError("invalid checkpoint batch position")

    weighted_loss = float(resume_weighted_loss)
    total_targets = int(resume_targets)
    batches_completed = int(resume_batches_completed)
    last_learning_rate = getattr(job.optimizer, "learning_rate", None)
    last_loss = 0.0

    session_start = time.time()
    session_completed = 0
    interactive = bool(sys.stdout.isatty())

    job.begin_training()

    try:
        for batch_index in range(start_batch_index, total_batches):
            sequences = sequence_batches[batch_index]
            batch = job.batch_builder.build(sequences)
            if batch.batch_size() == 0:
                continue

            metrics = job.trainer.train_batch(batch)
            count = int(metrics["active_targets"])
            last_loss = float(metrics["loss"])
            last_learning_rate = metrics["learning_rate"]

            weighted_loss += last_loss * count
            total_targets += count
            batches_completed += 1
            session_completed += 1

            current_batch = batch_index + 1
            elapsed = time.time() - session_start
            per_batch = elapsed / max(1, session_completed)
            remaining = max(0, total_batches - current_batch)
            eta = per_batch * remaining
            mean_loss = (
                weighted_loss / total_targets
                if total_targets > 0
                else 0.0
            )
            percent = 100.0 * current_batch / max(1, total_batches)

            metric_record = {
                "timestamp_unix": time.time(),
                "epoch": epoch_index + 1,
                "epochs": epochs,
                "batch": current_batch,
                "total_batches": total_batches,
                "percent": percent,
                "loss": last_loss,
                "mean_loss": mean_loss,
                "learning_rate": last_learning_rate,
                "global_step": int(metrics["global_step"]),
                "active_targets": count,
                "device": compute_status.get("active"),
                "elapsed_seconds": elapsed,
                "eta_seconds": eta,
            }
            write_metric(metrics_path, metric_record)

            should_draw = (
                current_batch == total_batches
                or current_batch == start_batch_index + 1
                or current_batch % args.progress_every == 0
            )

            if should_draw:
                line = (
                    f"EPOCH {epoch_index + 1}/{epochs} "
                    f"{progress_bar(current_batch, total_batches)} "
                    f"{current_batch}/{total_batches} {percent:6.2f}% "
                    f"loss={last_loss:.6f} avg={mean_loss:.6f} "
                    f"lr={float(last_learning_rate):.6g} "
                    f"elapsed={format_duration(elapsed)} "
                    f"ETA={format_duration(eta)} "
                    f"device={compute_status.get('active')}"
                )
                if interactive:
                    print("\r" + line.ljust(180), end="", flush=True)
                else:
                    print(line, flush=True)

            should_checkpoint = (
                args.checkpoint_every > 0
                and current_batch < total_batches
                and current_batch % args.checkpoint_every == 0
            )

            if should_checkpoint:
                if interactive:
                    print()
                step_path = save_progress_checkpoint(
                    manager,
                    job_id,
                    output_path,
                    progress_path,
                    args,
                    tokenizer_path,
                    train_sequences,
                    validation_sequences,
                    compute_status,
                    epoch_index,
                    current_batch,
                    total_batches,
                    weighted_loss,
                    total_targets,
                    batches_completed,
                    last_loss,
                )
                print("[CHECKPOINT]", step_path, flush=True)

        if interactive:
            print()

        if batches_completed == 0:
            raise ValueError("training epoch requires at least one non-empty batch")

        job.trainer.state.epoch += 1
        mean_loss = weighted_loss / total_targets if total_targets > 0 else 0.0

        result = {
            "epoch": job.trainer.state.epoch,
            "batches": batches_completed,
            "active_targets": total_targets,
            "loss": mean_loss,
            "learning_rate": last_learning_rate,
            "global_step": job.trainer.state.global_step,
        }
        job.record("train_epoch", result)
        job.end_training()
        return result

    except Exception as error:
        job.fail(str(error))
        raise


def main():
    parser = argparse.ArgumentParser(
        description=(
            "Train the real SireSoft-IKON-v1.0 decoder-only language model "
            "with CPU/CUDA compute, live progress and resumable checkpoints."
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
        default="model_store/manifests/sirellm_tokenizer.sltok",
    )
    parser.add_argument(
        "--records-per-dataset",
        type=int,
        default=250,
        help="Real canonical records per dataset. Use 0 for all records.",
    )
    parser.add_argument("--epochs", type=int, default=1)
    parser.add_argument("--batch-size", type=int, default=4)
    parser.add_argument("--sequence-length", type=int, default=64)
    parser.add_argument("--d-model", type=int, default=32)
    parser.add_argument("--layers", type=int, default=2)
    parser.add_argument("--heads", type=int, default=4)
    parser.add_argument("--d-ff", type=int, default=128)
    parser.add_argument("--learning-rate", type=float, default=0.001)
    parser.add_argument(
        "--validation-every",
        type=int,
        default=20,
        help="Every Nth accepted source record becomes validation data.",
    )
    parser.add_argument("--seed", type=int, default=1337)
    parser.add_argument(
        "--device",
        choices=("auto", "cpu", "cuda"),
        default="auto",
        help=(
            "Compute device. auto uses the custom CUDA backend when available "
            "and otherwise falls back to CPU."
        ),
    )
    parser.add_argument(
        "--cuda-device-index",
        type=int,
        default=0,
        help="CUDA device index used when --device is auto/cuda.",
    )
    parser.add_argument(
        "--resume",
        default=None,
        help="Explicit .lbckpt checkpoint to resume from.",
    )
    parser.add_argument(
        "--auto-resume",
        action="store_true",
        help=(
            "Automatically resume from sirellm-v1-progress.lbckpt when it exists."
        ),
    )
    parser.add_argument(
        "--checkpoint-every",
        type=int,
        default=100,
        help="Save a resumable checkpoint every N training batches. 0 disables it.",
    )
    parser.add_argument(
        "--keep-step-checkpoints",
        type=int,
        default=5,
        help="Keep the newest N numbered step checkpoints. The progress checkpoint is always kept.",
    )
    parser.add_argument(
        "--progress-every",
        type=int,
        default=1,
        help="Refresh/print the live training visualization every N batches.",
    )
    parser.add_argument(
        "--training-log",
        default="model_store/checkpoints/sirellm-v1-training.jsonl",
        help="Live JSONL metrics log written during training.",
    )
    parser.add_argument(
        "--output",
        default="model_store/checkpoints/sirellm-v1.lbckpt",
    )
    args = parser.parse_args()

    if args.records_per_dataset < 0:
        raise ValueError("--records-per-dataset must be >= 0")
    if args.epochs <= 0:
        raise ValueError("--epochs must be > 0")
    if args.batch_size <= 0:
        raise ValueError("--batch-size must be > 0")
    if args.sequence_length <= 1:
        raise ValueError("--sequence-length must be > 1")
    if args.d_model % args.heads != 0:
        raise ValueError("--d-model must be divisible by --heads")
    if args.checkpoint_every < 0:
        raise ValueError("--checkpoint-every must be >= 0")
    if args.keep_step_checkpoints < 0:
        raise ValueError("--keep-step-checkpoints must be >= 0")
    if args.progress_every <= 0:
        raise ValueError("--progress-every must be > 0")

    enter_project_root()

    token_ns = load_tokenizer_namespace()
    tokenizer_manager = token_ns["build_tokenizer_manager"]()

    tokenizer_path = ROOT / args.tokenizer
    tokenizer_manager.load_state_file(str(tokenizer_path))

    tokenizer_info = tokenizer_manager.info()
    vocabulary = tokenizer_manager.model.vocabulary
    pad_id = vocabulary.special_id("<PAD>")

    train_sequences, validation_sequences, counts = load_sequences(
        tokenizer_manager,
        args.datasets,
        args.records_per_dataset,
        args.sequence_length,
        args.validation_every,
    )

    if not train_sequences:
        raise RuntimeError("No trainable token sequences were produced.")
    if not validation_sequences:
        validation_sequences = train_sequences[:1]

    train_batches = make_batches(train_sequences, args.batch_size)
    validation_batches = make_batches(validation_sequences, args.batch_size)

    total_steps = max(1, len(train_batches) * args.epochs)
    warmup_steps = min(100, max(1, total_steps // 20))

    config = {
        "model": {
            "vocab_size": tokenizer_info["vocabulary_size"],
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
            "min_learning_rate": args.learning_rate * 0.1,
            "warmup_steps": warmup_steps,
            "decay_steps": total_steps,
            "start_learning_rate": args.learning_rate * 0.1,
        },
        "training": {
            "device": args.device,
            "cuda_device_index": args.cuda_device_index,
            "pad_token_id": pad_id,
            "ignore_index": -100,
            "max_sequence_length": args.sequence_length,
            "gradient_clip_norm": 1.0,
        },
    }

    train_ns = load_training_namespace()
    compute_backend = train_ns.get("GPU_BACKEND")
    if compute_backend is not None:
        compute_status = compute_backend.configure(
            args.device,
            args.cuda_device_index,
            strict=(args.device == "cuda"),
        )
    else:
        compute_status = {
            "requested": args.device,
            "active": "cpu",
            "device_index": args.cuda_device_index,
            "library": None,
        }

    manager = train_ns["TrainingJobManager"]()
    job_id = "sirellm-v1"
    job = manager.create_job(job_id, config)

    output_path = ROOT / args.output
    output_path.parent.mkdir(parents=True, exist_ok=True)
    progress_path = output_path.with_name(
        output_path.stem + "-progress" + output_path.suffix
    )
    metrics_path = ROOT / args.training_log

    resume_path = None
    if args.resume:
        resume_path = ROOT / args.resume
    elif args.auto_resume and progress_path.is_file():
        resume_path = progress_path

    resume_metadata = {}
    if resume_path is not None:
        if not resume_path.is_file():
            raise FileNotFoundError("Resume checkpoint not found: " + str(resume_path))
        loaded = manager.load_checkpoint(job_id, str(resume_path))
        resume_metadata = loaded.get("metadata", {}) or {}

    print("SireSoft-IKON-v1.0 REAL MODEL TRAINING")
    print("compute requested:", compute_status.get("requested"))
    print("compute active:", compute_status.get("active"))
    print("cuda device index:", compute_status.get("device_index"))
    print("cuda backend:", compute_status.get("library"))
    print("vocab size:", tokenizer_info["vocabulary_size"])
    print("parameters:", job.model.parameter_count())
    print("train sequences:", len(train_sequences))
    print("validation sequences:", len(validation_sequences))
    print("train batches:", len(train_batches))
    print("epochs:", args.epochs)
    print(
        "model:",
        args.layers,
        "layers /",
        args.d_model,
        "d_model /",
        args.heads,
        "heads",
    )
    print("checkpoint every:", args.checkpoint_every, "batches")
    print("progress checkpoint:", progress_path)
    print("training metrics:", metrics_path)
    if resume_path is not None:
        print("resumed from:", resume_path)
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

    start_epoch_index = int(
        resume_metadata.get("resume_epoch_index", job.trainer.state.epoch)
    )
    resume_batch_index = int(resume_metadata.get("next_batch_index", 0))
    resume_weighted_loss = float(resume_metadata.get("epoch_weighted_loss", 0.0))
    resume_targets = int(resume_metadata.get("epoch_targets", 0))
    resume_batches_completed = int(
        resume_metadata.get("epoch_batches_completed", 0)
    )

    if start_epoch_index >= args.epochs:
        print(
            "[RESUME] Requested training is already complete in the checkpoint "
            f"(completed epochs={job.trainer.state.epoch})."
        )
    else:
        for epoch_index in range(start_epoch_index, args.epochs):
            epoch_number = epoch_index + 1
            start_batch = resume_batch_index if epoch_index == start_epoch_index else 0

            if start_batch > 0:
                print(
                    f"[RESUME] Epoch {epoch_number}/{args.epochs} from batch "
                    f"{start_batch + 1}/{len(train_batches)}"
                )

            print(
                f"[EPOCH {epoch_number}/{args.epochs}] training "
                f"{len(train_batches)} batches...",
                flush=True,
            )

            train_metrics = train_epoch_live(
                manager,
                job_id,
                train_batches,
                epoch_index,
                args.epochs,
                start_batch,
                output_path,
                progress_path,
                metrics_path,
                args,
                tokenizer_path,
                train_sequences,
                validation_sequences,
                compute_status,
                resume_weighted_loss if epoch_index == start_epoch_index else 0.0,
                resume_targets if epoch_index == start_epoch_index else 0,
                resume_batches_completed if epoch_index == start_epoch_index else 0,
            )

            validation_metrics = manager.evaluate(job_id, validation_batches)

            epoch_path = output_path.with_name(
                output_path.stem
                + "-epoch-"
                + str(epoch_number).zfill(3)
                + output_path.suffix
            )

            metadata = common_metadata(
                args,
                tokenizer_path,
                train_sequences,
                validation_sequences,
                compute_status,
            )
            metadata.update({
                "checkpoint_kind": "epoch_complete",
                "epoch_requested": epoch_number,
                "resume_epoch_index": epoch_index + 1,
                "next_batch_index": 0,
                "total_batches_per_epoch": len(train_batches),
                "epoch_weighted_loss": 0.0,
                "epoch_targets": 0,
                "epoch_batches_completed": 0,
                "train_loss": float(train_metrics["loss"]),
                "validation_loss": float(validation_metrics["loss"]),
            })

            manager.save_checkpoint(job_id, str(epoch_path), metadata=metadata)
            manager.save_checkpoint(job_id, str(output_path), metadata=metadata)
            manager.save_checkpoint(job_id, str(progress_path), metadata=metadata)

            print(
                f"[EPOCH {epoch_number}] train_loss={train_metrics['loss']:.6f} "
                f"val_loss={validation_metrics['loss']:.6f} "
                f"global_step={train_metrics['global_step']} "
                f"lr={float(train_metrics['learning_rate']):.6g}"
            )
            print("checkpoint:", epoch_path)
            print("latest:", output_path)
            print()

            resume_batch_index = 0
            resume_weighted_loss = 0.0
            resume_targets = 0
            resume_batches_completed = 0

    manager.complete(job_id)

    final_compute_status = (
        compute_backend.status()
        if compute_backend is not None
        else compute_status
    )
    kernel_calls = final_compute_status.get("calls", {}) or {}

    if final_compute_status.get("active") == "cuda":
        required_cuda_calls = (
            "matmul",
            "attention_forward",
            "cross_entropy_forward",
            "adamw",
        )
        missing_cuda_calls = [
            name
            for name in required_cuda_calls
            if int(kernel_calls.get(name, 0)) <= 0
        ]
        if missing_cuda_calls:
            raise RuntimeError(
                "CUDA was active but required training kernels were not exercised: "
                + ", ".join(missing_cuda_calls)
            )

    print("MODEL TRAINING COMPLETE")
    print("final checkpoint:", output_path)
    print("resumable latest:", progress_path)
    print("training metrics:", metrics_path)
    print("compute active:", final_compute_status.get("active"))
    if kernel_calls:
        print("CUDA/backend kernel calls:")
        for name in sorted(kernel_calls):
            print(" ", name, "=", kernel_calls[name])


if __name__ == "__main__":
    main()
