"""Smoke-test SireSoft-IKON compute paths.

Examples:
  python tools/test_compute_backend.py --device cpu
  python tools/test_compute_backend.py --device cuda

The CPU test intentionally requires no GPU and no compiled CUDA library.
"""

import argparse
from real_runtime import enter_project_root, load_training_namespace


def close(a, b, tolerance=1e-5):
    return abs(float(a) - float(b)) <= tolerance


def assert_close_list(actual, expected, tolerance=1e-5):
    if len(actual) != len(expected):
        raise AssertionError("length mismatch")
    for index in range(len(actual)):
        if not close(actual[index], expected[index], tolerance):
            raise AssertionError(
                "value mismatch at " + str(index)
                + ": " + repr(actual[index])
                + " != " + repr(expected[index])
            )


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--device",
        choices=("cpu", "cuda", "auto"),
        default="cpu",
    )
    parser.add_argument("--cuda-device-index", type=int, default=0)
    args = parser.parse_args()

    enter_project_root()
    ns = load_training_namespace()
    backend = ns["GPU_BACKEND"]
    status = backend.configure(
        args.device,
        args.cuda_device_index,
        strict=(args.device == "cuda"),
    )
    backend.reset_call_stats()

    Tensor = ns["Tensor"]
    Value = ns["Value"]
    LayerNorm = ns["LayerNorm"]
    ScaledDotProductAttention = ns["ScaledDotProductAttention"]
    CrossEntropyLoss = ns["CrossEntropyLoss"]
    TrainingJobManager = ns["TrainingJobManager"]

    # Core tensor math.
    a = Tensor([[1.0, 2.0], [3.0, 4.0]])
    b = Tensor([[5.0, 6.0], [7.0, 8.0]])
    assert_close_list(
        a.matmul(b).flatten(),
        [19.0, 22.0, 43.0, 50.0],
        2e-4,
    )

    # Autograd through matmul + broadcast + reduction.
    x = Value([[1.0, 2.0], [3.0, 4.0]])
    w = Value([[0.5, -1.0], [1.5, 2.0]])
    y = (x @ w).add(Value([0.25, -0.5], requires_grad=False))
    loss = y.sum()
    loss.backward()
    assert_close_list(x.grad.flatten(), [-0.5, 3.5, -0.5, 3.5], 2e-4)

    # LayerNorm forward/backward.
    ln = LayerNorm(4)
    ln_x = Value([[1.0, 2.0, 3.0, 4.0], [4.0, 3.0, 2.0, 1.0]])
    ln_y = ln(ln_x)
    ln_y.sum().backward()
    if len(ln_x.grad.flatten()) != 8:
        raise AssertionError("LayerNorm gradient size mismatch")

    # Attention forward/backward.
    q = Value([[[1.0, 0.0], [0.0, 1.0]]])
    k = Value([[[1.0, 0.0], [0.0, 1.0]]])
    v = Value([[[1.0, 2.0], [3.0, 4.0]]])
    attention = ScaledDotProductAttention(causal=True)
    attn_out = attention(q, k, v)
    attn_out.sum().backward()
    if len(q.grad.flatten()) != 4 or len(v.grad.flatten()) != 4:
        raise AssertionError("attention gradient size mismatch")

    # Cross entropy forward/backward.
    logits = Value([[2.0, 1.0, 0.0], [0.0, 1.0, 2.0]])
    ce = CrossEntropyLoss(reduction="mean")
    ce_loss = ce(logits, [0, 2])
    if not (0.0 < ce_loss.item() < 2.0):
        raise AssertionError("cross entropy loss outside expected range")
    ce_loss.backward()
    if len(logits.grad.flatten()) != 6:
        raise AssertionError("cross entropy gradient size mismatch")

    # One real miniature Transformer training step. This exercises embedding,
    # attention, LayerNorm, autograd, gradient clipping and AdamW together.
    config = {
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
        "scheduler": {"type": "constant", "learning_rate": 0.001},
        "training": {
            "pad_token_id": 0,
            "ignore_index": -100,
            "max_sequence_length": 8,
            "gradient_clip_norm": 1.0,
        },
    }

    manager = TrainingJobManager()
    manager.create_job("compute-smoke", config)
    metrics = manager.train_step(
        "compute-smoke",
        [
            [1, 2, 3, 4, 5],
            [2, 3, 4, 5, 6],
        ],
    )
    if metrics["global_step"] != 1:
        raise AssertionError("training step did not advance")
    if not (metrics["loss"] >= 0.0):
        raise AssertionError("training loss is invalid")

    final_status = backend.status()
    print("SireSoft-IKON COMPUTE BACKEND TEST: PASS")
    print("requested:", final_status["requested"])
    print("active:", final_status["active"])
    print("device_index:", final_status["device_index"])
    print("cuda_library:", final_status["library"])
    print("training_loss:", metrics["loss"])
    print("backend_calls:", final_status["calls"])

    if args.device == "cpu" and final_status["active"] != "cpu":
        raise AssertionError("CPU test unexpectedly activated CUDA")
    if args.device == "cuda":
        if final_status["active"] != "cuda":
            raise AssertionError("CUDA test did not activate CUDA")
        required = (
            "matmul",
            "attention_forward",
            "attention_backward",
            "layernorm_forward",
            "cross_entropy_forward",
            "adamw",
        )
        for name in required:
            if final_status["calls"].get(name, 0) <= 0:
                raise AssertionError("CUDA kernel was not exercised: " + name)


if __name__ == "__main__":
    main()
