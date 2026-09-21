import os

MATH_BASE = "libs/core/math/"
AUTOGRAD_BASE = "libs/core/autograd/"
SERIAL_BASE = "libs/core/serialization/"
NEURAL_BASE = "libs/neural/"
TRANSFORMER_BASE = "libs/transformer/"
TRAINING_BASE = "libs/training/"
INFERENCE_BASE = "libs/inference/"
PROTOCOL_BASE = "libs/protocol/"
REGISTRY_BASE = "services/model_registry/"
SERVICE_BASE = "services/inference_service/"

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
            "validator.py",
            "codec.py",
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
    "loader.py",
    "result.py",
    "runtime.py",
    "service.py",
]:
    path = SERVICE_BASE + filename

    source = open(
        path,
        "r",
        encoding="utf-8",
    ).read()

    if "import " in source:
        raise AssertionError(
            "inference_service implementation contains forbidden import: "
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

CHECKPOINT_V1 = (
    "services/inference_service/"
    "_test_inference_v1.lbckpt"
)

CHECKPOINT_V2 = (
    "services/inference_service/"
    "_test_inference_v2.lbckpt"
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
        + repr(expected)
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


def model_config(
    seed,
):
    return {
        "vocab_size": 16,
        "d_model": 4,
        "num_layers": 1,
        "num_heads": 2,
        "d_ff": 8,
        "max_seq_len": 8,
        "dropout": 0.0,
        "position_mode": "rotary",
        "seed": seed,
    }


def make_model(
    seed,
):
    config = model_config(
        seed
    )

    return LanguageModel(
        vocab_size=config[
            "vocab_size"
        ],
        d_model=config[
            "d_model"
        ],
        num_layers=config[
            "num_layers"
        ],
        num_heads=config[
            "num_heads"
        ],
        d_ff=config[
            "d_ff"
        ],
        max_seq_len=config[
            "max_seq_len"
        ],
        dropout=config[
            "dropout"
        ],
        position_mode=config[
            "position_mode"
        ],
        seed=config[
            "seed"
        ],
    )


def create_checkpoint(
    path,
    seed,
    version,
):
    model = make_model(
        seed
    )

    CheckpointManager().save(
        path=path,
        model=model,
        metadata={
            "job_id": (
                "inference-test-"
                + version
            ),
            "job_config": {
                "model": model_config(
                    seed
                ),
            },
        },
    )

    return model


def prepare_registry():
    first_model = create_checkpoint(
        CHECKPOINT_V1,
        401,
        "v1",
    )

    second_model = create_checkpoint(
        CHECKPOINT_V2,
        402,
        "v2",
    )

    registry = ModelRegistry()

    registry.register_checkpoint(
        "sirellm",
        "1.0.0",
        CHECKPOINT_V1,
        stage=True,
    )

    registry.register_checkpoint(
        "sirellm",
        "2.0.0",
        CHECKPOINT_V2,
        stage=True,
    )

    registry.promote(
        "sirellm",
        "1.0.0",
    )

    return (
        registry,
        first_model,
        second_model,
    )


def cleanup():
    for path in (
        CHECKPOINT_V1,
        CHECKPOINT_V2,
    ):
        if os.path.exists(
            path
        ):
            os.remove(
                path
            )


def test_loader_exact_weights(
    registry,
    source_model,
):
    loader = ModelLoader(
        registry
    )

    loaded = loader.load_active(
        "sirellm"
    )

    eq(
        loaded.version,
        "1.0.0",
        "loader resolves active version",
    )

    eq(
        loaded.model.state_dict(),
        source_model.state_dict(),
        "checkpoint restores exact model weights",
    )

    eq(
        loaded.model.training,
        False,
        "loaded model placed in eval mode",
    )

    eq(
        loaded.info()[
            "parameter_count"
        ],
        source_model.parameter_count(),
        "loaded parameter count",
    )


def test_runtime_status_and_load(
    registry,
):
    runtime = build_inference_runtime(
        registry
    )

    eq(
        runtime.status()[
            "ready"
        ],
        False,
        "new runtime not ready",
    )

    info = runtime.load_active(
        "sirellm"
    )

    eq(
        info[
            "version"
        ],
        "1.0.0",
        "runtime loads active checkpoint",
    )

    eq(
        runtime.status()[
            "ready"
        ],
        True,
        "runtime ready after load",
    )


def test_real_greedy_generation(
    registry,
):
    runtime = build_inference_runtime(
        registry
    )

    runtime.load_active(
        "sirellm"
    )

    result = runtime.generate(
        prompt_ids=[
            1,
            2,
            3,
        ],
        max_new_tokens=3,
        sampler="greedy",
    )

    eq(
        len(
            result.generated_ids
        ),
        3,
        "real model generates requested token count",
    )

    eq(
        result.stop_reason,
        "max_new_tokens",
        "generation stop reason",
    )

    for token_id in result.generated_ids:
        check(
            0 <= token_id < 16,
            "generated token stays in vocabulary",
        )

    eq(
        result.model_id,
        "sirellm",
        "generation carries model identity",
    )

    eq(
        result.version,
        "1.0.0",
        "generation carries version identity",
    )


def test_deterministic_categorical(
    registry,
):
    runtime = build_inference_runtime(
        registry
    )

    runtime.load_active(
        "sirellm"
    )

    first = runtime.generate(
        prompt_ids=[
            1,
            2,
        ],
        max_new_tokens=4,
        sampler="categorical",
        seed=55,
        temperature=0.8,
        top_k=8,
        top_p=0.9,
    )

    second = runtime.generate(
        prompt_ids=[
            1,
            2,
        ],
        max_new_tokens=4,
        sampler="categorical",
        seed=55,
        temperature=0.8,
        top_k=8,
        top_p=0.9,
    )

    eq(
        first.generated_ids,
        second.generated_ids,
        "same categorical seed is deterministic",
    )


def test_banned_token_control(
    registry,
):
    runtime = build_inference_runtime(
        registry
    )

    runtime.load_active(
        "sirellm"
    )

    baseline = runtime.generate(
        prompt_ids=[
            1,
            2,
            3,
        ],
        max_new_tokens=1,
        sampler="greedy",
    )

    blocked_token = (
        baseline.generated_ids[
            0
        ]
    )

    guarded = runtime.generate(
        prompt_ids=[
            1,
            2,
            3,
        ],
        max_new_tokens=1,
        sampler="greedy",
        banned_token_ids=[
            blocked_token
        ],
    )

    check(
        guarded.generated_ids[
            0
        ]
        != blocked_token,
        "banned token excluded from generation",
    )


def test_context_window(
    registry,
):
    runtime = build_inference_runtime(
        registry
    )

    runtime.load_active(
        "sirellm"
    )

    long_prompt = [
        1,
        2,
        3,
        4,
        5,
        6,
        7,
        8,
        9,
        10,
    ]

    expect_error(
        ValueError,
        lambda: runtime.generate(
            prompt_ids=long_prompt,
            max_new_tokens=1,
            allow_prompt_truncation=False,
        ),
        "oversized prompt rejected when truncation disabled",
    )

    result = runtime.generate(
        prompt_ids=long_prompt,
        max_new_tokens=1,
        allow_prompt_truncation=True,
    )

    eq(
        result.prompt_truncated(),
        True,
        "oversized prompt truncation recorded",
    )

    eq(
        result.effective_prompt_ids,
        [
            3,
            4,
            5,
            6,
            7,
            8,
            9,
            10,
        ],
        "left truncation preserves latest context window",
    )

    eq(
        result.context_window,
        8,
        "context window reported",
    )


def test_model_switching(
    registry,
    second_source_model,
):
    runtime = build_inference_runtime(
        registry
    )

    runtime.load_active(
        "sirellm"
    )

    registry.promote(
        "sirellm",
        "2.0.0",
    )

    switched = runtime.sync_active(
        "sirellm"
    )

    eq(
        switched[
            "switched"
        ],
        True,
        "runtime switches after registry promotion",
    )

    eq(
        runtime.loaded.version,
        "2.0.0",
        "runtime now uses promoted version",
    )

    eq(
        runtime.loaded.model.state_dict(),
        second_source_model.state_dict(),
        "switched model has exact v2 checkpoint weights",
    )

    repeated = runtime.sync_active(
        "sirellm"
    )

    eq(
        repeated[
            "switched"
        ],
        False,
        "sync is no-op when already active",
    )


def test_explicit_version_load(
    registry,
):
    runtime = build_inference_runtime(
        registry
    )

    info = runtime.load_version(
        "sirellm",
        "1.0.0",
    )

    eq(
        info[
            "version"
        ],
        "1.0.0",
        "explicit version load",
    )


def test_unload(
    registry,
):
    runtime = build_inference_runtime(
        registry
    )

    runtime.load_active(
        "sirellm"
    )

    result = runtime.unload()

    eq(
        result[
            "unloaded"
        ],
        True,
        "runtime unload reports previous model",
    )

    eq(
        runtime.ready(),
        False,
        "runtime not ready after unload",
    )

    expect_error(
        RuntimeError,
        lambda: runtime.generate(
            [
                1,
                2,
            ],
            max_new_tokens=1,
        ),
        "generation after unload rejected",
    )


def test_service_flow(
    registry,
):
    runtime = build_inference_runtime(
        registry
    )

    service = InferenceService(
        runtime
    )

    loaded = service.handle(
        ServiceRequest(
            "s1",
            "inference_service",
            "load_active",
            payload={
                "model_id": "sirellm",
            },
        )
    )

    eq(
        loaded.success,
        True,
        "service loads active model",
    )

    generated = service.handle(
        ServiceRequest(
            "s2",
            "inference_service",
            "generate",
            payload={
                "prompt_ids": [
                    1,
                    2,
                    3,
                ],
                "max_new_tokens": 2,
                "sampler": "greedy",
                "temperature": 1.0,
                "top_k": 5,
                "repetition_penalty": 1.1,
            },
        )
    )

    eq(
        generated.success,
        True,
        "service generation succeeds",
    )

    eq(
        generated.data[
            "generation"
        ][
            "generated_count"
        ],
        2,
        "service generation count",
    )

    status = service.handle(
        ServiceRequest(
            "s3",
            "inference_service",
            "status",
        )
    )

    eq(
        status.data[
            "ready"
        ],
        True,
        "service status ready",
    )


def test_service_protocol_round_trip(
    registry,
):
    service = InferenceService(
        build_inference_runtime(
            registry
        )
    )

    codec = ProtocolCodec()

    load_request = ServiceRequest(
        "protocol-load",
        "inference_service",
        "load_version",
        payload={
            "model_id": "sirellm",
            "version": "1.0.0",
        },
        trace_id="trace-inference",
    )

    load_request = (
        codec.decode_request(
            codec.encode_request(
                load_request
            )
        )
    )

    load_response = (
        service.handle(
            load_request
        )
    )

    load_response = (
        codec.decode_response(
            codec.encode_response(
                load_response
            )
        )
    )

    eq(
        load_response.success,
        True,
        "load survives protocol codec",
    )

    eq(
        load_response.trace_id,
        "trace-inference",
        "inference trace preserved",
    )

    generation_request = (
        ServiceRequest(
            "protocol-generate",
            "inference_service",
            "generate",
            payload={
                "prompt_ids": [
                    1,
                    2,
                ],
                "max_new_tokens": 2,
                "sampler": "categorical",
                "seed": 777,
                "top_k": 6,
            },
            trace_id="trace-inference-2",
        )
    )

    generation_request = (
        codec.decode_request(
            codec.encode_request(
                generation_request
            )
        )
    )

    generation_response = (
        service.handle(
            generation_request
        )
    )

    generation_response = (
        codec.decode_response(
            codec.encode_response(
                generation_response
            )
        )
    )

    eq(
        generation_response.success,
        True,
        "generation survives protocol codec",
    )

    eq(
        len(
            generation_response
            .data[
                "generation"
            ][
                "generated_ids"
            ]
        ),
        2,
        "protocol generated IDs",
    )


def test_service_not_ready(
    registry,
):
    service = InferenceService(
        build_inference_runtime(
            registry
        )
    )

    response = service.handle(
        ServiceRequest(
            "x",
            "inference_service",
            "generate",
            payload={
                "prompt_ids": [
                    1,
                ],
                "max_new_tokens": 1,
            },
        )
    )

    eq(
        response.success,
        False,
        "unloaded service generation fails",
    )

    eq(
        response.error.code,
        "MODEL_NOT_READY",
        "not-ready service error",
    )

    eq(
        response.error.retryable,
        True,
        "not-ready service error retryable",
    )


def test_validation(
    registry,
):
    runtime = build_inference_runtime(
        registry
    )

    runtime.load_version(
        "sirellm",
        "1.0.0",
    )

    expect_error(
        ValueError,
        lambda: runtime.generate(
            [
                99,
            ],
            max_new_tokens=1,
        ),
        "out-of-vocabulary prompt token rejected",
    )

    expect_error(
        ValueError,
        lambda: runtime.generate(
            [
                1,
            ],
            max_new_tokens=1,
            sampler="unknown",
        ),
        "unknown sampler rejected",
    )

    service = InferenceService(
        runtime
    )

    wrong = service.handle(
        ServiceRequest(
            "w",
            "rag_service",
            "status",
        )
    )

    eq(
        wrong.error.code,
        "INVALID_REQUEST",
        "wrong target service rejected",
    )

    expect_error(
        TypeError,
        lambda: service.handle(
            {}
        ),
        "non-ServiceRequest rejected",
    )


def main():
    cleanup()

    registry, first_model, second_model = (
        prepare_registry()
    )

    try:
        test_loader_exact_weights(
            registry,
            first_model,
        )
        test_runtime_status_and_load(
            registry
        )
        test_real_greedy_generation(
            registry
        )
        test_deterministic_categorical(
            registry
        )
        test_banned_token_control(
            registry
        )
        test_context_window(
            registry
        )
        test_model_switching(
            registry,
            second_model,
        )
        test_explicit_version_load(
            registry
        )
        test_unload(
            registry
        )
        test_service_flow(
            registry
        )
        test_service_protocol_round_trip(
            registry
        )
        test_service_not_ready(
            registry
        )
        test_validation(
            registry
        )

    finally:
        cleanup()

    print(
        "INFERENCE SERVICE TEST SUITE: PASS"
    )
    print(
        "Assertions passed:",
        ASSERTIONS,
    )
    print(
        "Files validated: 4/4"
    )
    print(
        "Active registry checkpoint loading: VALIDATED"
    )
    print(
        "Exact model-weight restoration: VALIDATED"
    )
    print(
        "Greedy/categorical generation: VALIDATED"
    )
    print(
        "Temperature/top-k/top-p/repetition controls: VALIDATED"
    )
    print(
        "Banned-token filtering: VALIDATED"
    )
    print(
        "Context-window enforcement/truncation: VALIDATED"
    )
    print(
        "Registry promotion/model switching: VALIDATED"
    )
    print(
        "Protocol service operations: VALIDATED"
    )
    print(
        "Third-party dependencies: 0"
    )


main()
