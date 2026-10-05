"""CPU-only test for live progress/checkpoint/resume logic.

This test intentionally requires no GPU and no datasets. It trains a tiny model,
saves a mid-epoch checkpoint, restores it into a fresh training job, and proves
that training resumes from the next batch rather than restarting the epoch.
"""

import tempfile
from pathlib import Path

from real_runtime import enter_project_root, load_training_namespace


def config():
    return {
        "model": {
            "vocab_size": 32,
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
            "pad_token_id": 0,
            "ignore_index": -100,
            "max_sequence_length": 8,
            "gradient_clip_norm": 1.0,
        },
    }


def main():
    enter_project_root()
    ns = load_training_namespace()
    ns["GPU_BACKEND"].configure("cpu", 0)
    Manager = ns["TrainingJobManager"]

    batches = [
        [[1, 2, 3, 4], [2, 3, 4, 5]],
        [[3, 4, 5, 6], [4, 5, 6, 7]],
        [[5, 6, 7, 8], [6, 7, 8, 9]],
    ]

    first = Manager()
    job = first.create_job("recovery-test", config())

    job.begin_training()
    for sequences in batches[:2]:
        batch = job.batch_builder.build(sequences)
        job.trainer.train_batch(batch)
    job.end_training()

    if job.trainer.state.global_step != 2:
        raise AssertionError("expected two completed steps before checkpoint")

    with tempfile.TemporaryDirectory() as directory:
        checkpoint = Path(directory) / "resume.lbckpt"
        first.save_checkpoint(
            "recovery-test",
            str(checkpoint),
            metadata={
                "resume_epoch_index": 0,
                "next_batch_index": 2,
                "epoch_batches_completed": 2,
            },
        )

        second = Manager()
        restored = second.create_job("recovery-test", config())
        loaded = second.load_checkpoint("recovery-test", str(checkpoint))

        metadata = loaded["metadata"]
        if restored.trainer.state.global_step != 2:
            raise AssertionError("global step was not restored")
        if int(metadata.get("next_batch_index", -1)) != 2:
            raise AssertionError("next batch position was not restored")

        final_metrics = second.train_step("recovery-test", batches[2])
        if final_metrics["global_step"] != 3:
            raise AssertionError("resume did not continue at the next global step")

    print("TRAINING CHECKPOINT/RESUME TEST: PASS")
    print("GPU required: no")
    print("restored global step: 2")
    print("continued global step: 3")


if __name__ == "__main__":
    main()
