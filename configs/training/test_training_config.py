MATH_BASE = "libs/core/math/"
AUTOGRAD_BASE = "libs/core/autograd/"
SERIAL_BASE = "libs/core/serialization/"
PARSERS_BASE = "libs/data/parsers/"
NEURAL_BASE = "libs/neural/"
TRANSFORMER_BASE = "libs/transformer/"
LOSS_BASE = "libs/training/losses/"
OPT_BASE = "libs/training/optimizers/"
SCHEDULE_BASE = "libs/training/schedules/"
BATCH_BASE = "libs/training/batching/"
TRAINING_BASE = "libs/training/"
SERVICE_BASE = "services/training_service/"
CONFIG_BASE = "configs/training/"

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
        PARSERS_BASE,
        [
            "json_parser.py",
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
        SERVICE_BASE,
        [
            "job.py",
            "factory.py",
            "manager.py",
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
    "model.py",
    "optimizer.py",
    "scheduler.py",
    "loop.py",
    "config.py",
    "codec.py",
    "validator.py",
    "factory.py",
]:
    path = CONFIG_BASE + filename

    source = open(
        path,
        "r",
        encoding="utf-8",
    ).read()

    if "import " in source:
        raise AssertionError(
            "training config implementation contains forbidden import: "
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

globals().update(
    namespace
)

ASSERTIONS = 0


def check(
    condition,
    message,
):
    global ASSERTIONS
    ASSERTIONS += 1

    if not condition:
        raise AssertionError(
            message
        )


def eq(
    actual,
    expected,
    message,
):
    check(
        actual == expected,
        message
        + " | got="
        + repr(actual)
        + " expected="
        + repr(expected),
    )


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

    except Exception as error:
        raise AssertionError(
            message
            + " | wrong exception="
            + repr(error)
        )

    raise AssertionError(
        message
        + " | expected exception was not raised"
    )


def sample_config():
    return TrainingJobConfig(
        model=TrainingModelConfig(
            vocab_size=12,
            d_model=4,
            num_layers=1,
            num_heads=2,
            d_ff=8,
            max_seq_len=8,
            dropout=0.0,
            position_mode="rotary",
            seed=501,
        ),
        optimizer=OptimizerConfig(
            optimizer_type="adamw",
            learning_rate=0.03,
            weight_decay=0.0,
        ),
        scheduler=SchedulerConfig(
            scheduler_type=(
                "linear_warmup"
            ),
            target_learning_rate=0.03,
            warmup_steps=2,
            start_learning_rate=0.01,
        ),
        training=TrainingLoopConfig(
            pad_token_id=0,
            ignore_index=-100,
            max_sequence_length=4,
            gradient_clip_norm=1.0,
            padding_side="right",
        ),
        metadata={
            "purpose": (
                "config-integration-test"
            ),
        },
    )


def test_model_config():
    model = TrainingModelConfig(
        vocab_size=100,
        d_model=32,
        num_layers=2,
        num_heads=4,
    )

    eq(
        model.d_ff,
        128,
        "default feed-forward width",
    )

    expect_error(
        ValueError,
        lambda: TrainingModelConfig(
            vocab_size=100,
            d_model=10,
            num_heads=4,
        ),
        "d_model/head incompatibility rejected",
    )


def test_optimizer_config():
    adam = OptimizerConfig(
        "adamw",
        learning_rate=0.01,
    )

    eq(
        adam.to_dict()[
            "type"
        ],
        "adamw",
        "AdamW config type",
    )

    sgd = OptimizerConfig(
        "sgd",
        learning_rate=0.1,
        momentum=0.9,
        nesterov=True,
        weight_decay=0.0,
    )

    eq(
        sgd.to_dict()[
            "nesterov"
        ],
        True,
        "SGD nesterov preserved",
    )


def test_scheduler_config():
    scheduler = SchedulerConfig(
        "warmup_cosine",
        max_learning_rate=0.02,
        min_learning_rate=0.001,
        warmup_steps=3,
        decay_steps=40,
        start_learning_rate=0.001,
    )

    output = scheduler.to_dict(
        base_learning_rate=0.02
    )

    eq(
        output[
            "type"
        ],
        "warmup_cosine",
        "scheduler type serialized",
    )

    eq(
        output[
            "decay_steps"
        ],
        40,
        "scheduler decay steps",
    )


def test_codec():
    text = (
        '{"model":{'
        '"vocab_size":12,"d_model":4,"num_layers":1,'
        '"num_heads":2,"d_ff":8,"max_seq_len":8,'
        '"dropout":0.0,"position_mode":"rotary","seed":700'
        '},'
        '"optimizer":{'
        '"type":"sgd","learning_rate":0.02,'
        '"momentum":0.0,"weight_decay":0.0'
        '},'
        '"scheduler":{'
        '"type":"cosine","max_learning_rate":0.02,'
        '"min_learning_rate":0.001,"total_steps":20'
        '},'
        '"training":{'
        '"pad_token_id":0,"ignore_index":-100,'
        '"max_sequence_length":4,"gradient_clip_norm":1.0'
        '},'
        '"metadata":{"source":"typed-json"}'
        '}'
    )

    config = (
        TrainingConfigCodec()
        .decode_text(
            text
        )
    )

    eq(
        config.optimizer.optimizer_type,
        "sgd",
        "codec optimizer type",
    )

    eq(
        config.scheduler.scheduler_type,
        "cosine",
        "codec scheduler type",
    )

    eq(
        config.metadata[
            "source"
        ],
        "typed-json",
        "codec metadata",
    )


def test_cross_validation():
    invalid = TrainingJobConfig(
        model=TrainingModelConfig(
            vocab_size=10,
            d_model=4,
            num_heads=2,
            max_seq_len=4,
        ),
        training=TrainingLoopConfig(
            pad_token_id=11,
            max_sequence_length=5,
        ),
    )

    result = (
        TrainingConfigValidator()
        .validate(
            invalid
        )
    )

    eq(
        result[
            "valid"
        ],
        False,
        "cross-section invalid config rejected",
    )

    codes = [
        item[
            "code"
        ]
        for item
        in result[
            "errors"
        ]
    ]

    check(
        "PAD_TOKEN_OUT_OF_RANGE"
        in codes,
        "pad-token range error detected",
    )

    check(
        "TRAIN_SEQUENCE_EXCEEDS_MODEL_LIMIT"
        in codes,
        "sequence/model length conflict detected",
    )


def test_factory_dict():
    output = (
        TrainingConfigFactory()
        .build_factory_dict(
            sample_config()
        )
    )

    eq(
        output[
            "model"
        ][
            "vocab_size"
        ],
        12,
        "factory dict model mapped",
    )

    eq(
        output[
            "scheduler"
        ][
            "type"
        ],
        "linear_warmup",
        "factory dict scheduler mapped",
    )

    check(
        "metadata"
        not in output,
        "training service factory receives executable sections only",
    )


def test_real_job_creation():
    job = (
        TrainingConfigFactory()
        .create_job(
            "typed-config-job",
            sample_config(),
        )
    )

    eq(
        job.status,
        "ready",
        "typed config creates ready training job",
    )

    eq(
        job.model.vocab_size,
        12,
        "typed config builds real language model",
    )

    eq(
        type(
            job.optimizer
        ).__name__,
        "AdamW",
        "typed config builds AdamW",
    )

    eq(
        type(
            job.scheduler
        ).__name__,
        "LinearWarmupSchedule",
        "typed config builds warmup scheduler",
    )

    check(
        job.model.parameter_count()
        > 0,
        "typed config creates model parameters",
    )


def test_manager_real_training_step():
    manager = (
        TrainingJobManager()
    )

    job = (
        TrainingConfigFactory()
        .create_manager_job(
            manager,
            "manager-job",
            sample_config(),
        )
    )

    before = list(
        job.model
        .lm_head
        .weight
        .data
        .flatten()
    )

    metrics = manager.train_step(
        "manager-job",
        [
            [
                1,
                2,
                3,
                4,
                5,
            ],
            [
                2,
                3,
                4,
                5,
                6,
            ],
        ],
    )

    after = (
        job.model
        .lm_head
        .weight
        .data
        .flatten()
    )

    check(
        metrics[
            "loss"
        ]
        > 0.0,
        "typed config executes real training loss",
    )

    eq(
        metrics[
            "global_step"
        ],
        1,
        "typed config real training advances global step",
    )

    check(
        before != after,
        "typed config training updates model weights",
    )

    check(
        metrics[
            "grad_norm_after"
        ]
        <= 1.000001,
        "typed config gradient clipping applied",
    )


def test_none_scheduler():
    config = TrainingJobConfig(
        model=TrainingModelConfig(
            vocab_size=12,
            d_model=4,
            num_layers=1,
            num_heads=2,
            d_ff=8,
            max_seq_len=8,
        ),
        optimizer=OptimizerConfig(
            "sgd",
            learning_rate=0.01,
            weight_decay=0.0,
        ),
        scheduler=SchedulerConfig(
            "none"
        ),
        training=TrainingLoopConfig(
            max_sequence_length=4,
        ),
    )

    job = (
        TrainingConfigFactory()
        .create_job(
            "no-schedule",
            config,
        )
    )

    eq(
        job.scheduler,
        None,
        "disabled scheduler maps to no runtime scheduler",
    )


def main():
    test_model_config()
    test_optimizer_config()
    test_scheduler_config()
    test_codec()
    test_cross_validation()
    test_factory_dict()
    test_real_job_creation()
    test_manager_real_training_step()
    test_none_scheduler()

    print(
        "TRAINING CONFIG TEST SUITE: PASS"
    )
    print(
        "Assertions passed:",
        ASSERTIONS,
    )
    print(
        "Files validated: 8/8"
    )
    print(
        "Typed model/optimizer/scheduler/loop config: VALIDATED"
    )
    print(
        "Handwritten JSON decoding: VALIDATED"
    )
    print(
        "Cross-section training validation: VALIDATED"
    )
    print(
        "TrainingFactory integration: VALIDATED"
    )
    print(
        "Real Transformer job creation: VALIDATED"
    )
    print(
        "Real forward/backward optimizer step: VALIDATED"
    )
    print(
        "Gradient clipping + scheduler mapping: VALIDATED"
    )
    print(
        "Third-party dependencies: 0"
    )


main()
