import os

MATH_BASE = "libs/core/math/"
AUTOGRAD_BASE = "libs/core/autograd/"
SERIAL_BASE = "libs/core/serialization/"
NEURAL_BASE = "libs/neural/"
TRANSFORMER_BASE = "libs/transformer/"
LOSS_BASE = "libs/training/losses/"
OPT_BASE = "libs/training/optimizers/"
SCHEDULE_BASE = "libs/training/schedules/"
BATCH_BASE = "libs/training/batching/"
TRAINING_BASE = "libs/training/"
PROTOCOL_BASE = "libs/protocol/"
SERVICE_BASE = "services/training_service/"

namespace = {"__builtins__": __builtins__}

groups = [
    (MATH_BASE, ["scalar.py", "random.py", "tensor.py"]),
    (
        AUTOGRAD_BASE,
        ["operation.py", "value.py", "graph.py", "backward.py"],
    ),
    (
        SERIAL_BASE,
        ["binary_writer.py", "binary_reader.py", "checksum.py"],
    ),
    (
        NEURAL_BASE,
        [
            "parameter.py",
            "layer.py",
            "initializers.py",
            "activations.py",
            "linear.py",
            "embedding.py",
            "dropout.py",
            "layer_norm.py",
        ],
    ),
    (
        TRANSFORMER_BASE,
        [
            "positional_encoding.py",
            "rotary_embedding.py",
            "causal_mask.py",
            "attention.py",
            "multi_head_attention.py",
            "feed_forward.py",
            "transformer_block.py",
            "decoder.py",
            "language_model.py",
        ],
    ),
    (LOSS_BASE, ["softmax.py", "cross_entropy.py"]),
    (OPT_BASE, ["sgd.py", "adamw.py"]),
    (
        SCHEDULE_BASE,
        ["constant.py", "warmup.py", "cosine.py"],
    ),
    (
        BATCH_BASE,
        ["padding.py", "sequence_packer.py", "batch_builder.py"],
    ),
    (
        TRAINING_BASE,
        [
            "gradient_clipping.py",
            "trainer.py",
            "evaluator.py",
            "checkpoint.py",
        ],
    ),
    (
        PROTOCOL_BASE,
        [
            "error.py",
            "message.py",
            "request.py",
            "response.py",
            "validator.py",
            "codec.py",
        ],
    ),
]

for base, filenames in groups:
    for filename in filenames:
        path = base + filename
        source = open(path, "r", encoding="utf-8").read()
        exec(compile(source, path, "exec"), namespace)

for filename in [
    "job.py",
    "factory.py",
    "manager.py",
    "service.py",
]:
    path = SERVICE_BASE + filename
    source = open(path, "r", encoding="utf-8").read()

    if "import " in source:
        raise AssertionError(
            "training_service implementation contains forbidden import: "
            + filename
        )

    exec(compile(source, path, "exec"), namespace)

globals().update(namespace)

ASSERTIONS = 0
CHECKPOINT_PATH = (
    "services/training_service/"
    "_test_training_checkpoint.lbckpt"
)


def check(condition, message):
    global ASSERTIONS
    ASSERTIONS += 1
    if not condition:
        raise AssertionError(message)


def eq(actual, expected, message):
    check(
        actual == expected,
        message
        + " | got="
        + repr(actual)
        + " expected="
        + repr(expected),
    )


def close(actual, expected, tolerance=1e-7):
    difference = actual - expected
    if difference < 0:
        difference = -difference
    return difference <= tolerance


def expect_error(error_type, fn, message):
    global ASSERTIONS
    ASSERTIONS += 1

    try:
        fn()
    except error_type:
        return
    except Exception as exc:
        raise AssertionError(
            message
            + " | wrong exception="
            + repr(exc)
        )

    raise AssertionError(
        message
        + " | expected exception was not raised"
    )


def config(seed=101, optimizer="adamw", scheduler="constant"):
    schedule = {"type": scheduler}

    if scheduler == "constant":
        schedule["learning_rate"] = 0.03
    elif scheduler == "linear_warmup":
        schedule.update({
            "target_learning_rate": 0.03,
            "warmup_steps": 2,
            "start_learning_rate": 0.01,
        })
    elif scheduler == "cosine":
        schedule.update({
            "max_learning_rate": 0.03,
            "min_learning_rate": 0.005,
            "total_steps": 20,
        })
    elif scheduler == "warmup_cosine":
        schedule.update({
            "max_learning_rate": 0.03,
            "min_learning_rate": 0.005,
            "warmup_steps": 2,
            "decay_steps": 20,
            "start_learning_rate": 0.005,
        })

    opt = {
        "type": optimizer,
        "learning_rate": 0.03,
        "weight_decay": 0.0,
    }

    if optimizer == "sgd":
        opt["momentum"] = 0.0

    return {
        "model": {
            "vocab_size": 12,
            "d_model": 4,
            "num_layers": 1,
            "num_heads": 2,
            "d_ff": 8,
            "max_seq_len": 8,
            "dropout": 0.0,
            "position_mode": "rotary",
            "seed": seed,
        },
        "optimizer": opt,
        "scheduler": schedule,
        "training": {
            "pad_token_id": 0,
            "ignore_index": -100,
            "max_sequence_length": 4,
            "gradient_clip_norm": 1.0,
        },
    }


def sequences():
    return [
        [1, 2, 3, 4, 5],
        [2, 3, 4, 5, 6],
    ]


def one_sequence():
    return [[1, 2, 3, 4]]


def test_factory():
    job = TrainingFactory().create(
        "factory",
        config(seed=111, scheduler="linear_warmup"),
    )

    eq(job.status, "ready", "factory job ready")
    eq(job.model.vocab_size, 12, "model vocab")
    eq(type(job.optimizer).__name__, "AdamW", "AdamW built")
    eq(
        type(job.scheduler).__name__,
        "LinearWarmupSchedule",
        "warmup schedule built",
    )
    check(
        job.model.parameter_count() > 0,
        "real model has parameters",
    )

    other = TrainingFactory().create(
        "sgd",
        config(
            seed=112,
            optimizer="sgd",
            scheduler="cosine",
        ),
    )

    eq(type(other.optimizer).__name__, "SGD", "SGD supported")
    eq(
        type(other.scheduler).__name__,
        "CosineDecaySchedule",
        "cosine supported",
    )


def test_manager_and_real_step():
    manager = TrainingJobManager()

    job = manager.create_job(
        "step",
        config(seed=131, scheduler="linear_warmup"),
    )

    before = list(
        job.model.lm_head.weight.data.flatten()
    )

    metrics = manager.train_step(
        "step",
        sequences(),
    )

    after = job.model.lm_head.weight.data.flatten()

    check(metrics["loss"] > 0.0, "training loss positive")
    check(before != after, "weights update")
    eq(metrics["global_step"], 1, "global step")
    check(
        close(metrics["learning_rate"], 0.01),
        "warmup LR applied",
    )
    check(
        metrics["grad_norm_after"] <= 1.000001,
        "gradient clipping",
    )
    eq(job.status, "ready", "job ready after step")

    listed = manager.list_jobs()
    eq(len(listed), 1, "job listed")

    expect_error(
        ValueError,
        lambda: manager.create_job(
            "step",
            config(),
        ),
        "duplicate job rejected",
    )


def test_loss_reduction_and_eval():
    manager = TrainingJobManager()

    manager.create_job(
        "reduce",
        config(seed=141),
    )

    initial = manager.evaluate(
        "reduce",
        [one_sequence()],
    )["loss"]

    step = 0
    while step < 8:
        manager.train_step(
            "reduce",
            one_sequence(),
        )
        step += 1

    final = manager.evaluate(
        "reduce",
        [one_sequence()],
    )["loss"]

    check(
        final < initial,
        "repeated training reduces loss",
    )

    check(
        manager.get("reduce")
        .trainer
        .state
        .best_validation_loss
        is not None,
        "best validation tracked",
    )


def test_epoch():
    manager = TrainingJobManager()

    manager.create_job(
        "epoch",
        config(seed=151, optimizer="sgd"),
    )

    metrics = manager.train_epoch(
        "epoch",
        [sequences(), sequences()],
    )

    eq(metrics["batches"], 2, "epoch batch count")
    eq(metrics["epoch"], 1, "epoch number")
    eq(
        manager.get("epoch").trainer.state.global_step,
        2,
        "epoch advances global step",
    )


def test_checkpoint():
    if os.path.exists(CHECKPOINT_PATH):
        os.remove(CHECKPOINT_PATH)

    manager = TrainingJobManager()
    job = manager.create_job(
        "checkpoint",
        config(seed=171, scheduler="linear_warmup"),
    )

    manager.train_step(
        "checkpoint",
        one_sequence(),
    )

    saved_step = job.trainer.state.global_step
    saved_weights = list(
        job.model.lm_head.weight.data.flatten()
    )

    info = manager.save_checkpoint(
        "checkpoint",
        CHECKPOINT_PATH,
        metadata={"purpose": "test"},
    )

    check(info["bytes"] > 0, "checkpoint wrote bytes")

    manager.train_step(
        "checkpoint",
        one_sequence(),
    )

    check(
        job.trainer.state.global_step > saved_step,
        "state advanced after save",
    )

    manager.load_checkpoint(
        "checkpoint",
        CHECKPOINT_PATH,
    )

    eq(
        job.trainer.state.global_step,
        saved_step,
        "trainer state restored",
    )
    eq(
        job.model.lm_head.weight.data.flatten(),
        saved_weights,
        "weights restored",
    )


def test_completion():
    manager = TrainingJobManager()
    manager.create_job(
        "complete",
        config(seed=181),
    )

    eq(
        manager.complete("complete")["status"],
        "completed",
        "job completed",
    )

    expect_error(
        RuntimeError,
        lambda: manager.train_step(
            "complete",
            one_sequence(),
        ),
        "completed job cannot train",
    )


def test_service():
    service = TrainingService()

    created = service.handle(
        ServiceRequest(
            "s1",
            "training_service",
            "create_job",
            payload={
                "job_id": "service-job",
                "config": config(seed=191),
            },
        )
    )

    eq(created.success, True, "service create job")

    trained = service.handle(
        ServiceRequest(
            "s2",
            "training_service",
            "train_step",
            payload={
                "job_id": "service-job",
                "sequences": one_sequence(),
            },
        )
    )

    eq(trained.success, True, "service train")
    eq(
        trained.data["metrics"]["global_step"],
        1,
        "service train metrics",
    )

    evaluated = service.handle(
        ServiceRequest(
            "s3",
            "training_service",
            "evaluate",
            payload={
                "job_id": "service-job",
                "sequence_batches": [one_sequence()],
            },
        )
    )

    eq(evaluated.success, True, "service evaluate")

    status = service.handle(
        ServiceRequest(
            "s4",
            "training_service",
            "status",
            payload={"job_id": "service-job"},
        )
    )

    eq(
        status.data["job"]["training_state"]["global_step"],
        1,
        "service status",
    )


def test_protocol():
    service = TrainingService()
    codec = ProtocolCodec()

    request = ServiceRequest(
        "protocol-create",
        "training_service",
        "create_job",
        payload={
            "job_id": "protocol-job",
            "config": config(
                seed=201,
                scheduler="warmup_cosine",
            ),
        },
        trace_id="trace-training",
    )

    request = codec.decode_request(
        codec.encode_request(request)
    )

    response = service.handle(request)

    response = codec.decode_response(
        codec.encode_response(response)
    )

    eq(response.success, True, "protocol service success")
    eq(
        response.trace_id,
        "trace-training",
        "trace preserved",
    )
    eq(
        response.data["job"]["scheduler"],
        "WarmupThenSchedule",
        "warmup cosine preserved",
    )


def test_errors():
    service = TrainingService()

    missing = service.handle(
        ServiceRequest(
            "e1",
            "training_service",
            "status",
            payload={"job_id": "missing"},
        )
    )

    eq(
        missing.error.code,
        "NOT_FOUND",
        "missing job error",
    )

    wrong = service.handle(
        ServiceRequest(
            "e2",
            "rag_service",
            "status",
        )
    )

    eq(
        wrong.error.code,
        "INVALID_REQUEST",
        "wrong service rejected",
    )

    invalid = service.handle(
        ServiceRequest(
            "e3",
            "training_service",
            "create_job",
            payload={
                "job_id": "bad",
                "config": {
                    "model": {
                        "vocab_size": 0,
                    },
                },
            },
        )
    )

    eq(
        invalid.error.code,
        "INVALID_REQUEST",
        "bad config rejected",
    )


def test_validation():
    expect_error(
        ValueError,
        lambda: TrainingFactory().create(
            "x",
            {"model": {}},
        ),
        "missing vocab size rejected",
    )

    expect_error(
        KeyError,
        lambda: TrainingJobManager().train_epoch(
            "missing",
            [],
        ),
        "missing job rejected",
    )

    expect_error(
        TypeError,
        lambda: TrainingService().handle(
            {}
        ),
        "non-ServiceRequest rejected",
    )


def main():
    try:
        test_factory()
        test_manager_and_real_step()
        test_loss_reduction_and_eval()
        test_epoch()
        test_checkpoint()
        test_completion()
        test_service()
        test_protocol()
        test_errors()
        test_validation()

    finally:
        if os.path.exists(CHECKPOINT_PATH):
            os.remove(CHECKPOINT_PATH)

    print("TRAINING SERVICE TEST SUITE: PASS")
    print("Assertions passed:", ASSERTIONS)
    print("Files validated: 4/4")
    print("Real Transformer job creation: VALIDATED")
    print("AdamW/SGD optimizer setup: VALIDATED")
    print("Constant/warmup/cosine schedules: VALIDATED")
    print("Real train step/epoch execution: VALIDATED")
    print("Loss reduction + evaluation: VALIDATED")
    print("Gradient clipping/state accounting: VALIDATED")
    print("Checkpoint save/resume: VALIDATED")
    print("Protocol service operations: VALIDATED")
    print("Third-party dependencies: 0")


main()
