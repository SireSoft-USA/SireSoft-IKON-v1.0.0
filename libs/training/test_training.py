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

namespace = {
    "__builtins__": __builtins__,
}

groups = [
    (
        MATH_BASE,
        [
            "scalar.py",
            "random.py",
            "tensor.py",
        ],
    ),
    (
        AUTOGRAD_BASE,
        [
            "operation.py",
            "value.py",
            "graph.py",
            "backward.py",
        ],
    ),
    (
        SERIAL_BASE,
        [
            "binary_writer.py",
            "binary_reader.py",
            "checksum.py",
        ],
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
    (
        LOSS_BASE,
        [
            "softmax.py",
            "cross_entropy.py",
        ],
    ),
    (
        OPT_BASE,
        [
            "sgd.py",
            "adamw.py",
        ],
    ),
    (
        SCHEDULE_BASE,
        [
            "constant.py",
            "warmup.py",
            "cosine.py",
        ],
    ),
    (
        BATCH_BASE,
        [
            "padding.py",
            "sequence_packer.py",
            "batch_builder.py",
        ],
    ),
]

for base, filenames in groups:
    for filename in filenames:
        path = base + filename
        source = open(
            path,
            "r",
            encoding="utf-8",
        ).read()

        exec(
            compile(
                source,
                path,
                "exec",
            ),
            namespace,
        )

for filename in [
    "gradient_clipping.py",
    "trainer.py",
    "evaluator.py",
    "checkpoint.py",
]:
    path = TRAINING_BASE + filename

    source = open(
        path,
        "r",
        encoding="utf-8",
    ).read()

    if "import " in source:
        raise AssertionError(
            "training implementation contains forbidden import: "
            + filename
        )

    exec(
        compile(
            source,
            path,
            "exec",
        ),
        namespace,
    )

globals().update(namespace)

ASSERTIONS = 0


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
        + repr(expected)
    )


def close(
    actual,
    expected,
    tolerance=1e-7,
):
    difference = actual - expected

    if difference < 0:
        difference = -difference

    return difference <= tolerance


def list_close(
    actual,
    expected,
    tolerance=1e-9,
):
    if len(actual) != len(expected):
        return False

    i = 0

    while i < len(actual):
        if not close(
            actual[i],
            expected[i],
            tolerance,
        ):
            return False

        i += 1

    return True


def expect_error(
    error_type,
    fn,
    message,
):
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


def build_model(seed=101):
    return LanguageModel(
        vocab_size=12,
        d_model=4,
        num_layers=1,
        num_heads=2,
        d_ff=8,
        max_seq_len=8,
        dropout=0.0,
        position_mode="rotary",
        seed=seed,
    )


def build_batch():
    return BatchBuilder(
        pad_token_id=0,
        ignore_index=-100,
        max_sequence_length=4,
    ).build(
        [
            [1, 2, 3, 4, 5],
            [2, 3, 4, 5, 6],
        ]
    )


def test_global_norm_clipper():
    first = Parameter(
        [1.0, 2.0],
        "first",
    )

    second = Parameter(
        [3.0],
        "second",
    )

    first.grad = Tensor(
        [3.0, 4.0],
        [2],
    )

    second.grad = Tensor(
        [12.0],
        [1],
    )

    clipper = GlobalNormClipper(
        5.0
    )

    result = clipper.clip(
        [first, second]
    )

    check(
        close(
            result.norm_before,
            13.0,
        ),
        "global norm before",
    )

    check(
        result.norm_after
        <= 5.0000001,
        "global norm clipped",
    )

    check(
        result.scale < 1.0,
        "global norm scale",
    )


def test_value_clipper():
    parameter = Parameter(
        [0.0, 0.0, 0.0],
        "p",
    )

    parameter.grad = Tensor(
        [-5.0, 0.5, 7.0],
        [3],
    )

    ValueClipper(
        1.0
    ).clip(
        [parameter]
    )

    check(
        list_close(
            parameter.grad.flatten(),
            [-1.0, 0.5, 1.0],
        ),
        "value clipping",
    )


def test_real_transformer_training_step():
    model = build_model(
        seed=111
    )

    batch = build_batch()

    optimizer = AdamW(
        model,
        learning_rate=0.02,
        weight_decay=0.0,
        max_grad_norm=None,
    )

    schedule = LinearWarmupSchedule(
        target_learning_rate=0.02,
        warmup_steps=2,
        start_learning_rate=0.01,
    )

    trainer = Trainer(
        model=model,
        optimizer=optimizer,
        loss_function=CrossEntropyLoss(
            ignore_index=-100,
        ),
        scheduler=schedule,
        gradient_clipper=GlobalNormClipper(
            1.0
        ),
    )

    before = [
        value
        for value
        in model.lm_head.weight.data.flatten()
    ]

    metrics = trainer.train_batch(
        batch
    )

    after = (
        model.lm_head.weight.data.flatten()
    )

    check(
        metrics["loss"] > 0.0,
        "training loss positive",
    )

    check(
        not list_close(
            before,
            after,
        ),
        "real Transformer parameters updated",
    )

    eq(
        trainer.state.global_step,
        1,
        "trainer global step",
    )

    eq(
        trainer.state.batches_seen,
        1,
        "trainer batch count",
    )

    eq(
        trainer.state.tokens_seen,
        batch.active_target_count(),
        "trainer token accounting",
    )

    check(
        close(
            metrics["learning_rate"],
            0.01,
        ),
        "scheduler applied on first step",
    )

    check(
        metrics["grad_norm_after"]
        <= 1.000001,
        "trainer gradient clipping",
    )


def test_repeated_training_reduces_loss():
    model = build_model(
        seed=121
    )

    batch = BatchBuilder(
        pad_token_id=0,
        ignore_index=-100,
        max_sequence_length=3,
    ).build(
        [
            [1, 2, 3, 4],
        ]
    )

    loss_fn = CrossEntropyLoss(
        ignore_index=-100,
    )

    evaluator = Evaluator(
        model,
        loss_fn,
    )

    initial = evaluator.evaluate_batch(
        batch
    )["loss"]

    optimizer = AdamW(
        model,
        learning_rate=0.03,
        weight_decay=0.0,
    )

    trainer = Trainer(
        model,
        optimizer,
        loss_fn,
        gradient_clipper=GlobalNormClipper(
            1.0
        ),
    )

    step = 0

    while step < 8:
        trainer.train_batch(
            batch
        )
        step += 1

    final = evaluator.evaluate_batch(
        batch
    )["loss"]

    check(
        final < initial,
        "repeated real Transformer training reduces loss",
    )


def test_train_epoch():
    model = build_model(
        seed=131
    )

    batch = build_batch()

    optimizer = SGD(
        model,
        learning_rate=0.005,
    )

    trainer = Trainer(
        model,
        optimizer,
        CrossEntropyLoss(
            ignore_index=-100,
        ),
    )

    metrics = trainer.train_epoch(
        [batch, batch]
    )

    eq(
        metrics["batches"],
        2,
        "train epoch batch count",
    )

    eq(
        trainer.state.epoch,
        1,
        "trainer epoch count",
    )

    eq(
        trainer.state.global_step,
        2,
        "train epoch global steps",
    )

    check(
        metrics["loss"] > 0.0,
        "train epoch loss",
    )


def test_evaluator_preserves_parameters_and_mode():
    model = build_model(
        seed=141
    )

    model.train()

    batch = build_batch()

    evaluator = Evaluator(
        model,
        CrossEntropyLoss(
            ignore_index=-100,
        ),
    )

    before = model.state_dict()

    metrics = evaluator.evaluate(
        [batch, batch]
    )

    after = model.state_dict()

    eq(
        before,
        after,
        "evaluation never updates parameters",
    )

    check(
        model.training,
        "evaluation restores train mode",
    )

    check(
        metrics["loss"] > 0.0,
        "evaluation loss",
    )

    check(
        metrics["perplexity"] > 1.0,
        "evaluation perplexity",
    )

    eq(
        metrics["batches"],
        2,
        "evaluation batch count",
    )


def test_validation_tracking():
    model = build_model(
        seed=151
    )

    trainer = Trainer(
        model,
        SGD(
            model,
            learning_rate=0.001,
        ),
        CrossEntropyLoss(),
    )

    check(
        trainer.record_validation_loss(
            4.0
        ),
        "first validation loss is best",
    )

    check(
        not trainer.record_validation_loss(
            5.0
        ),
        "worse validation loss not best",
    )

    check(
        trainer.record_validation_loss(
            3.5
        ),
        "better validation loss",
    )

    check(
        close(
            trainer.state.best_validation_loss,
            3.5,
        ),
        "best validation loss stored",
    )


def test_checkpoint_codec():
    codec = CheckpointCodec()

    payload = {
        "none": None,
        "bool": True,
        "integer": -123,
        "float": 1.25,
        "text": "SireLLM اردو",
        "bytes": b"\x00\x01\xff",
        "list": [1, 2, 3],
        "tuple": ("a", 2),
        "dict": {
            "nested": False,
        },
    }

    encoded = codec.encode(
        payload
    )

    decoded = codec.decode(
        encoded
    )

    eq(
        decoded,
        payload,
        "checkpoint codec round trip",
    )


def test_checkpoint_full_resume():
    path = (
        "libs/training/"
        "_test_training_checkpoint.lbckpt"
    )

    model = build_model(
        seed=161
    )

    batch = build_batch()

    optimizer = AdamW(
        model,
        learning_rate=0.02,
        weight_decay=0.01,
    )

    schedule = CosineDecaySchedule(
        max_learning_rate=0.02,
        min_learning_rate=0.005,
        total_steps=20,
    )

    trainer = Trainer(
        model,
        optimizer,
        CrossEntropyLoss(
            ignore_index=-100,
        ),
        scheduler=schedule,
    )

    trainer.train_batch(
        batch
    )
    trainer.train_batch(
        batch
    )

    expected_model = model.state_dict()
    expected_optimizer = (
        optimizer.state_dict()
    )
    expected_schedule = (
        schedule.state_dict()
    )
    expected_trainer = (
        trainer.state_dict()
    )

    manager = CheckpointManager()

    save_info = manager.save(
        path=path,
        model=model,
        optimizer=optimizer,
        scheduler=schedule,
        trainer=trainer,
        metadata={
            "purpose": "unit-test",
        },
    )

    check(
        save_info["bytes"] > 0,
        "checkpoint writes bytes",
    )

    # Corrupt all live state after saving.
    for parameter in model.parameters():
        zeros = [
            0.0
            for value
            in parameter.data.flatten()
        ]

        parameter.set_data(
            Tensor(
                zeros,
                [
                    dimension
                    for dimension
                    in parameter.shape
                ],
            )
        )

    optimizer.learning_rate = 9.0
    optimizer.step_count = 0
    schedule.max_learning_rate = 7.0
    trainer.state.global_step = 999

    payload = manager.load(
        path=path,
        model=model,
        optimizer=optimizer,
        scheduler=schedule,
        trainer=trainer,
    )

    eq(
        model.state_dict(),
        expected_model,
        "checkpoint restores model exactly",
    )

    eq(
        optimizer.state_dict(),
        expected_optimizer,
        "checkpoint restores optimizer exactly",
    )

    eq(
        schedule.state_dict(),
        expected_schedule,
        "checkpoint restores scheduler exactly",
    )

    eq(
        trainer.state_dict(),
        expected_trainer,
        "checkpoint restores trainer exactly",
    )

    eq(
        payload["metadata"]["purpose"],
        "unit-test",
        "checkpoint metadata",
    )


def test_checkpoint_corruption_detection():
    codec = CheckpointCodec()

    data = bytearray(
        codec.encode({
            "x": [1, 2, 3],
        })
    )

    data[-1] ^= 0x01

    expect_error(
        ValueError,
        lambda: codec.decode(
            bytes(data)
        ),
        "checkpoint checksum detects corruption",
    )


def test_trainer_state_round_trip():
    model = build_model(
        seed=171
    )

    trainer = Trainer(
        model,
        SGD(
            model,
            learning_rate=0.001,
        ),
        CrossEntropyLoss(),
    )

    trainer.state.global_step = 12
    trainer.state.epoch = 3
    trainer.state.tokens_seen = 500
    trainer.state.batches_seen = 12
    trainer.state.best_validation_loss = 1.75

    state = trainer.state_dict()

    other = Trainer(
        build_model(
            seed=172
        ),
        SGD(
            build_model(
                seed=173
            ).parameters(),
            learning_rate=0.001,
        ),
        CrossEntropyLoss(),
    )

    other.load_state_dict(
        state
    )

    eq(
        other.state_dict(),
        state,
        "trainer state round trip",
    )


def test_validation():
    model = build_model()

    expect_error(
        ValueError,
        lambda: GlobalNormClipper(
            0.0
        ),
        "invalid clip norm",
    )

    expect_error(
        TypeError,
        lambda: Trainer(
            None,
            SGD(
                model,
                learning_rate=0.001,
            ),
            CrossEntropyLoss(),
        ),
        "trainer rejects missing model",
    )

    expect_error(
        ValueError,
        lambda: Evaluator(
            model,
            CrossEntropyLoss(),
        ).evaluate(
            []
        ),
        "evaluator rejects empty batches",
    )


def main():
    test_global_norm_clipper()
    test_value_clipper()
    test_real_transformer_training_step()
    test_repeated_training_reduces_loss()
    test_train_epoch()
    test_evaluator_preserves_parameters_and_mode()
    test_validation_tracking()
    test_checkpoint_codec()
    test_checkpoint_full_resume()
    test_checkpoint_corruption_detection()
    test_trainer_state_round_trip()
    test_validation()

    print(
        "TRAINING ORCHESTRATION TEST SUITE: PASS"
    )
    print(
        "Assertions passed:",
        ASSERTIONS,
    )
    print(
        "Files validated: 4/4"
    )
    print(
        "Real Transformer training step: VALIDATED"
    )
    print(
        "Repeated loss reduction: VALIDATED"
    )
    print(
        "Gradient clipping: VALIDATED"
    )
    print(
        "Evaluation/perplexity: VALIDATED"
    )
    print(
        "Full checkpoint/resume: VALIDATED"
    )
    print(
        "Checkpoint corruption detection: VALIDATED"
    )
    print(
        "Third-party dependencies: 0"
    )


main()
