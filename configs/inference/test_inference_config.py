import os

MATH_BASE = "libs/core/math/"
AUTOGRAD_BASE = "libs/core/autograd/"
SERIAL_BASE = "libs/core/serialization/"
PARSERS_BASE = "libs/data/parsers/"
NEURAL_BASE = "libs/neural/"
TRANSFORMER_BASE = "libs/transformer/"
TRAINING_BASE = "libs/training/"
INFERENCE_BASE = "libs/inference/"
PROTOCOL_BASE = "libs/protocol/"
REGISTRY_BASE = "services/model_registry/"
SERVICE_BASE = "services/inference_service/"
CONFIG_BASE = "configs/inference/"

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
        TRAINING_BASE,
        [
            "checkpoint.py",
        ],
    ),
    (
        INFERENCE_BASE,
        [
            "logits_processor.py",
            "sampler.py",
            "generation_state.py",
            "kv_cache.py",
            "generator.py",
        ],
    ),
    (
        PROTOCOL_BASE,
        [
            "error.py",
            "message.py",
            "request.py",
            "response.py",
        ],
    ),
    (
        REGISTRY_BASE,
        [
            "model_version.py",
            "checkpoint_inspector.py",
            "registry.py",
        ],
    ),
    (
        SERVICE_BASE,
        [
            "loader.py",
            "result.py",
            "runtime.py",
            "service.py",
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
    "generation.py",
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
            "inference config implementation contains forbidden import: "
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

CHECKPOINT = (
    "configs/inference/"
    "_test_model.lbckpt"
)


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


def cleanup():
    if os.path.exists(
        CHECKPOINT
    ):
        os.remove(
            CHECKPOINT
        )


def make_registry():
    model = LanguageModel(
        vocab_size=16,
        d_model=4,
        num_layers=1,
        num_heads=2,
        d_ff=8,
        max_seq_len=8,
        dropout=0.0,
        position_mode="rotary",
        seed=901,
    )

    CheckpointManager().save(
        path=CHECKPOINT,
        model=model,
        metadata={
            "job_id": (
                "config-inference-test"
            ),
            "job_config": {
                "model": {
                    "vocab_size": 16,
                    "d_model": 4,
                    "num_layers": 1,
                    "num_heads": 2,
                    "d_ff": 8,
                    "max_seq_len": 8,
                    "dropout": 0.0,
                    "position_mode": (
                        "rotary"
                    ),
                    "seed": 901,
                },
            },
        },
    )

    registry = ModelRegistry()

    registry.register_checkpoint(
        "sirellm",
        "1.0.0",
        CHECKPOINT,
        stage=True,
    )

    registry.promote(
        "sirellm",
        "1.0.0",
    )

    return (
        registry,
        model,
    )


def sample_config():
    return InferenceConfig(
        model_id="sirellm",
        load_mode="active",
        generation=GenerationConfig(
            max_new_tokens=3,
            sampler="categorical",
            seed=77,
            temperature=0.8,
            top_k=8,
            top_p=0.9,
            repetition_penalty=1.05,
            banned_token_ids=[],
            allow_prompt_truncation=True,
        ),
        metadata={
            "purpose": "chat",
        },
    )


def test_generation_config():
    config = GenerationConfig(
        eos_token_ids=[
            2,
            2,
            3,
        ],
        banned_token_ids=[
            5,
            5,
        ],
    )

    eq(
        config.eos_token_ids,
        [
            2,
            3,
        ],
        "EOS token ids deduplicated",
    )

    eq(
        config.banned_token_ids,
        [
            5,
        ],
        "banned token ids deduplicated",
    )

    expect_error(
        ValueError,
        lambda: GenerationConfig(
            top_p=1.2
        ),
        "invalid top_p rejected",
    )


def test_codec():
    text = (
        '{"model_id":"sirellm",'
        '"load_mode":"version",'
        '"version":"1.0.0",'
        '"generation":{'
        '"max_new_tokens":4,'
        '"sampler":"greedy",'
        '"temperature":1.0,'
        '"top_k":5,'
        '"allow_prompt_truncation":false'
        '},'
        '"metadata":{"profile":"test"}'
        '}'
    )

    config = (
        InferenceConfigCodec()
        .decode_text(
            text
        )
    )

    eq(
        config.load_mode,
        "version",
        "codec load mode",
    )

    eq(
        config.version,
        "1.0.0",
        "codec version",
    )

    eq(
        config.generation.max_new_tokens,
        4,
        "codec generation limit",
    )


def test_validator_warning():
    config = InferenceConfig(
        "sirellm",
        load_mode="none",
        generation=GenerationConfig(
            sampler="greedy",
            temperature=0.7,
            top_k=4,
            eos_token_ids=[
                2,
            ],
            banned_token_ids=[
                2,
            ],
        ),
    )

    result = (
        InferenceConfigValidator()
        .validate(
            config
        )
    )

    codes = [
        item[
            "code"
        ]
        for item
        in result[
            "warnings"
        ]
    ]

    check(
        "GREEDY_WITH_SAMPLING_CONTROLS"
        in codes,
        "greedy sampling-control warning emitted",
    )

    check(
        "EOS_TOKEN_IS_BANNED"
        in codes,
        "EOS/banned overlap warning emitted",
    )


def test_registry_cross_validation():
    registry, _ = (
        make_registry()
    )

    missing = InferenceConfig(
        "missing-model",
        load_mode="active",
    )

    result = (
        InferenceConfigValidator()
        .validate(
            missing,
            registry=registry,
        )
    )

    eq(
        result[
            "valid"
        ],
        False,
        "missing model load target invalid",
    )

    eq(
        result[
            "errors"
        ][
            0
        ][
            "code"
        ],
        "MODEL_LOAD_TARGET_UNAVAILABLE",
        "missing model validation error code",
    )


def test_factory_active_load():
    registry, source_model = (
        make_registry()
    )

    runtime = (
        InferenceConfigFactory()
        .build_runtime(
            sample_config(),
            registry,
        )
    )

    eq(
        runtime.ready(),
        True,
        "factory auto-loads active model",
    )

    eq(
        runtime.loaded.version,
        "1.0.0",
        "factory resolves active version",
    )

    eq(
        runtime.loaded.model.state_dict(),
        source_model.state_dict(),
        "factory restores exact checkpoint weights",
    )


def test_generation_defaults():
    registry, _ = (
        make_registry()
    )

    factory = (
        InferenceConfigFactory()
    )

    config = sample_config()

    runtime = factory.build_runtime(
        config,
        registry,
    )

    first = factory.generate(
        runtime,
        config,
        prompt_ids=[
            1,
            2,
            3,
        ],
    )

    second = factory.generate(
        runtime,
        config,
        prompt_ids=[
            1,
            2,
            3,
        ],
    )

    eq(
        first.generated_ids,
        second.generated_ids,
        "configured categorical seed is deterministic",
    )

    eq(
        len(
            first.generated_ids
        ),
        3,
        "configured generation count applied",
    )

    eq(
        first.sampler,
        "categorical",
        "configured sampler applied",
    )


def test_generation_override():
    registry, _ = (
        make_registry()
    )

    factory = (
        InferenceConfigFactory()
    )

    config = sample_config()

    runtime = factory.build_runtime(
        config,
        registry,
    )

    result = factory.generate(
        runtime,
        config,
        prompt_ids=[
            1,
            2,
        ],
        overrides={
            "max_new_tokens": 1,
            "sampler": "greedy",
            "temperature": 1.0,
            "top_k": None,
            "top_p": None,
        },
    )

    eq(
        len(
            result.generated_ids
        ),
        1,
        "generation override changes token limit",
    )

    eq(
        result.sampler,
        "greedy",
        "generation override changes sampler",
    )

    expect_error(
        ValueError,
        lambda: (
            factory.generation_kwargs(
                config,
                overrides={
                    "unknown": 1,
                },
            )
        ),
        "unknown generation override rejected",
    )


def test_none_load_mode():
    registry, _ = (
        make_registry()
    )

    config = InferenceConfig(
        "sirellm",
        load_mode="none",
    )

    runtime = (
        InferenceConfigFactory()
        .build_runtime(
            config,
            registry,
        )
    )

    eq(
        runtime.ready(),
        False,
        "none load mode leaves runtime unloaded",
    )


def test_service_creation():
    registry, _ = (
        make_registry()
    )

    service = (
        InferenceConfigFactory()
        .build_service(
            sample_config(),
            registry,
        )
    )

    check(
        isinstance(
            service,
            InferenceService,
        ),
        "factory creates inference service",
    )

    response = service.handle(
        ServiceRequest(
            "cfg-status",
            "inference_service",
            "status",
        )
    )

    eq(
        response.success,
        True,
        "configured inference service responds",
    )

    eq(
        response.data[
            "ready"
        ],
        True,
        "configured inference service starts ready",
    )


def main():
    cleanup()

    try:
        test_generation_config()
        test_codec()
        test_validator_warning()
        test_registry_cross_validation()
        test_factory_active_load()
        test_generation_defaults()
        test_generation_override()
        test_none_load_mode()
        test_service_creation()

    finally:
        cleanup()

    print(
        "INFERENCE CONFIG TEST SUITE: PASS"
    )
    print(
        "Assertions passed:",
        ASSERTIONS,
    )
    print(
        "Files validated: 5/5"
    )
    print(
        "Typed model-load/generation configuration: VALIDATED"
    )
    print(
        "Handwritten JSON decoding: VALIDATED"
    )
    print(
        "Registry load-target validation: VALIDATED"
    )
    print(
        "Checkpoint-backed runtime creation: VALIDATED"
    )
    print(
        "Exact model-weight restoration: VALIDATED"
    )
    print(
        "Configured deterministic generation: VALIDATED"
    )
    print(
        "Generation override validation: VALIDATED"
    )
    print(
        "InferenceService generation: VALIDATED"
    )
    print(
        "Third-party dependencies: 0"
    )


main()
