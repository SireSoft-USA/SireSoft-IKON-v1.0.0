import os

MATH_BASE = "libs/core/math/"
AUTOGRAD_BASE = "libs/core/autograd/"
SERIAL_BASE = "libs/core/serialization/"
NEURAL_BASE = "libs/neural/"
TRANSFORMER_BASE = "libs/transformer/"
TRAINING_BASE = "libs/training/"
PROTOCOL_BASE = "libs/protocol/"
REGISTRY_BASE = "services/model_registry/"

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
    "model_version.py",
    "checkpoint_inspector.py",
    "registry.py",
    "service.py",
]:
    path = REGISTRY_BASE + filename

    source = open(
        path,
        "r",
        encoding="utf-8",
    ).read()

    if "import " in source:
        raise AssertionError(
            "model_registry implementation contains forbidden import: "
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
    "services/model_registry/"
    "_test_model_v1.lbckpt"
)

CHECKPOINT_V2 = (
    "services/model_registry/"
    "_test_model_v2.lbckpt"
)

MISSING_CHECKPOINT = (
    "services/model_registry/"
    "_missing_model.lbckpt"
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


def architecture(
    seed,
):
    return {
        "vocab_size": 24,
        "d_model": 4,
        "num_layers": 1,
        "num_heads": 2,
        "d_ff": 8,
        "max_seq_len": 16,
        "dropout": 0.0,
        "position_mode": "rotary",
        "seed": seed,
    }


def create_checkpoint(
    path,
    seed,
    version_name,
):
    model_config = architecture(
        seed
    )

    model = LanguageModel(
        vocab_size=model_config[
            "vocab_size"
        ],
        d_model=model_config[
            "d_model"
        ],
        num_layers=model_config[
            "num_layers"
        ],
        num_heads=model_config[
            "num_heads"
        ],
        d_ff=model_config[
            "d_ff"
        ],
        max_seq_len=model_config[
            "max_seq_len"
        ],
        dropout=model_config[
            "dropout"
        ],
        position_mode=model_config[
            "position_mode"
        ],
        seed=model_config[
            "seed"
        ],
    )

    info = CheckpointManager().save(
        path=path,
        model=model,
        metadata={
            "job_id": (
                "training-"
                + version_name
            ),
            "job_config": {
                "model": model_config,
                "optimizer": {
                    "type": "adamw",
                    "learning_rate": 0.001,
                },
            },
            "release_note": (
                "test checkpoint "
                + version_name
            ),
        },
    )

    return (
        model,
        info,
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


def prepare():
    cleanup()

    first = create_checkpoint(
        CHECKPOINT_V1,
        301,
        "v1",
    )

    second = create_checkpoint(
        CHECKPOINT_V2,
        302,
        "v2",
    )

    return (
        first,
        second,
    )


def test_model_version_state():
    item = ModelVersion(
        model_id="sirellm",
        version="1.0.0",
        checkpoint_path="model.ckpt",
        checkpoint_checksum="abc",
        checkpoint_bytes=100,
        parameter_count=50,
        architecture={
            "d_model": 4,
        },
        metadata={
            "note": "x",
        },
    )

    eq(
        item.key(),
        "sirellm@1.0.0",
        "model version key",
    )

    item.stage()

    eq(
        item.status,
        "staged",
        "stage transition",
    )

    item.activate()

    eq(
        item.status,
        "active",
        "activate transition",
    )

    item.deprecate()

    eq(
        item.status,
        "deprecated",
        "deprecate transition",
    )

    expect_error(
        RuntimeError,
        lambda: item.activate(),
        "deprecated version cannot reactivate",
    )


def test_checkpoint_inspection(
    model,
):
    inspector = (
        CheckpointInspector()
    )

    descriptor = inspector.inspect(
        CHECKPOINT_V1
    )

    eq(
        descriptor[
            "valid"
        ],
        True,
        "real checkpoint validates",
    )

    eq(
        descriptor[
            "format"
        ],
        "SireLLMCheckpoint",
        "checkpoint format",
    )

    eq(
        descriptor[
            "parameter_count"
        ],
        model.parameter_count(),
        "serialized parameter count matches real model",
    )

    eq(
        descriptor[
            "architecture"
        ][
            "d_model"
        ],
        4,
        "architecture extracted from training metadata",
    )

    eq(
        descriptor[
            "metadata"
        ][
            "job_id"
        ],
        "training-v1",
        "checkpoint metadata preserved",
    )

    check(
        len(
            descriptor[
                "checksum"
            ]
        )
        == 16,
        "checkpoint file checksum recorded",
    )


def test_discovery():
    inspector = (
        CheckpointInspector()
    )

    results = inspector.discover(
        [
            CHECKPOINT_V1,
            MISSING_CHECKPOINT,
        ]
    )

    eq(
        results[0][
            "valid"
        ],
        True,
        "discovery finds valid checkpoint",
    )

    eq(
        results[1][
            "valid"
        ],
        False,
        "discovery reports missing checkpoint",
    )

    eq(
        results[1][
            "error_type"
        ],
        "FileNotFoundError",
        "missing discovery error type",
    )


def test_register_and_list():
    registry = ModelRegistry()

    first = (
        registry
        .register_checkpoint(
            "sirellm",
            "1.0.0",
            CHECKPOINT_V1,
            metadata={
                "channel": "dev",
            },
            stage=True,
        )
    )

    second = (
        registry
        .register_checkpoint(
            "sirellm",
            "1.1.0",
            CHECKPOINT_V2,
        )
    )

    eq(
        first.status,
        "staged",
        "register with stage flag",
    )

    eq(
        second.status,
        "registered",
        "default registered state",
    )

    eq(
        first.metadata[
            "channel"
        ],
        "dev",
        "registration metadata merged",
    )

    eq(
        [
            item.version
            for item in registry.versions(
                "sirellm"
            )
        ],
        [
            "1.0.0",
            "1.1.0",
        ],
        "version order preserved",
    )

    models = registry.models()

    eq(
        models[0][
            "model_id"
        ],
        "sirellm",
        "model list identity",
    )

    eq(
        models[0][
            "version_count"
        ],
        2,
        "model version count",
    )


def test_promotion_and_deprecation():
    registry = ModelRegistry()

    registry.register_checkpoint(
        "sirellm",
        "1.0.0",
        CHECKPOINT_V1,
        stage=True,
    )

    registry.register_checkpoint(
        "sirellm",
        "1.1.0",
        CHECKPOINT_V2,
        stage=True,
    )

    registry.promote(
        "sirellm",
        "1.0.0",
    )

    eq(
        registry.active(
            "sirellm"
        ).version,
        "1.0.0",
        "first promotion active",
    )

    registry.promote(
        "sirellm",
        "1.1.0",
    )

    eq(
        registry.active(
            "sirellm"
        ).version,
        "1.1.0",
        "second promotion active",
    )

    eq(
        registry.get(
            "sirellm",
            "1.0.0",
        ).status,
        "staged",
        "previous active demoted to staged",
    )

    registry.deprecate(
        "sirellm",
        "1.0.0",
    )

    eq(
        registry.get(
            "sirellm",
            "1.0.0",
        ).status,
        "deprecated",
        "version deprecated",
    )

    expect_error(
        RuntimeError,
        lambda: registry.promote(
            "sirellm",
            "1.0.0",
        ),
        "deprecated version cannot promote",
    )


def test_verify_unchanged():
    registry = ModelRegistry()

    registry.register_checkpoint(
        "sirellm",
        "1.0.0",
        CHECKPOINT_V1,
    )

    result = registry.verify(
        "sirellm",
        "1.0.0",
    )

    eq(
        result[
            "valid"
        ],
        True,
        "unchanged registered checkpoint verifies",
    )

    eq(
        result[
            "checksum_match"
        ],
        True,
        "unchanged checksum matches",
    )

    eq(
        result[
            "parameter_count_match"
        ],
        True,
        "unchanged parameter count matches",
    )


def test_verify_corruption():
    registry = ModelRegistry()

    registry.register_checkpoint(
        "sirellm",
        "1.0.0",
        CHECKPOINT_V1,
    )

    handle = open(
        CHECKPOINT_V1,
        "rb",
    )

    try:
        data = bytearray(
            handle.read()
        )
    finally:
        handle.close()

    data[-1] ^= 0x01

    handle = open(
        CHECKPOINT_V1,
        "wb",
    )

    try:
        handle.write(
            data
        )
    finally:
        handle.close()

    result = registry.verify(
        "sirellm",
        "1.0.0",
    )

    eq(
        result[
            "valid"
        ],
        False,
        "corrupted registered checkpoint fails verification",
    )

    eq(
        result[
            "checkpoint_valid"
        ],
        False,
        "checkpoint codec rejects corruption",
    )


def test_registry_state_round_trip():
    # Recreate V1 because corruption test intentionally changed it.
    create_checkpoint(
        CHECKPOINT_V1,
        301,
        "v1",
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
        "1.1.0",
        CHECKPOINT_V2,
        stage=True,
    )

    registry.promote(
        "sirellm",
        "1.1.0",
    )

    state = registry.export_state()

    restored = ModelRegistry()
    restored.load_state(
        state
    )

    eq(
        restored.export_state(),
        state,
        "registry state exact round trip",
    )

    eq(
        restored.active(
            "sirellm"
        ).version,
        "1.1.0",
        "active version preserved in registry state",
    )


def test_protocol_safe_registry_state():
    registry = ModelRegistry()

    registry.register_checkpoint(
        "sirellm",
        "1.0.0",
        CHECKPOINT_V1,
    )

    state = registry.export_state()

    codec = ProtocolCodec()

    request = ServiceRequest(
        "state",
        "model_registry",
        "load_registry",
        payload={
            "state": state,
        },
    )

    restored = (
        codec.decode_request(
            codec.encode_request(
                request
            )
        )
    )

    eq(
        restored.payload[
            "state"
        ],
        state,
        "registry state survives protocol codec",
    )


def test_service_end_to_end():
    service = ModelRegistryService()

    registered = service.handle(
        ServiceRequest(
            "r1",
            "model_registry",
            "register_checkpoint",
            payload={
                "model_id": "sirellm",
                "version": "1.0.0",
                "checkpoint_path": CHECKPOINT_V1,
                "stage": True,
            },
        )
    )

    eq(
        registered.success,
        True,
        "service registers checkpoint",
    )

    promoted = service.handle(
        ServiceRequest(
            "r2",
            "model_registry",
            "promote_version",
            payload={
                "model_id": "sirellm",
                "version": "1.0.0",
            },
        )
    )

    eq(
        promoted.data[
            "model_version"
        ][
            "status"
        ],
        "active",
        "service promotes version",
    )

    active = service.handle(
        ServiceRequest(
            "r3",
            "model_registry",
            "active_version",
            payload={
                "model_id": "sirellm",
            },
        )
    )

    eq(
        active.data[
            "model_version"
        ][
            "version"
        ],
        "1.0.0",
        "service returns active version",
    )

    verified = service.handle(
        ServiceRequest(
            "r4",
            "model_registry",
            "verify_version",
            payload={
                "model_id": "sirellm",
                "version": "1.0.0",
            },
        )
    )

    eq(
        verified.data[
            "verification"
        ][
            "valid"
        ],
        True,
        "service verifies active version checkpoint",
    )


def test_service_protocol_round_trip():
    service = ModelRegistryService()
    codec = ProtocolCodec()

    request = ServiceRequest(
        "protocol-register",
        "model_registry",
        "register_checkpoint",
        payload={
            "model_id": "sirellm",
            "version": "2.0.0",
            "checkpoint_path": CHECKPOINT_V2,
            "metadata": {
                "release": "candidate",
            },
        },
        trace_id="trace-registry",
    )

    request = codec.decode_request(
        codec.encode_request(
            request
        )
    )

    response = service.handle(
        request
    )

    response = codec.decode_response(
        codec.encode_response(
            response
        )
    )

    eq(
        response.success,
        True,
        "model registry survives protocol codec",
    )

    eq(
        response.trace_id,
        "trace-registry",
        "model registry trace preserved",
    )

    eq(
        response.data[
            "model_version"
        ][
            "metadata"
        ][
            "release"
        ],
        "candidate",
        "service metadata survives protocol",
    )


def test_service_discovery():
    service = ModelRegistryService()

    response = service.handle(
        ServiceRequest(
            "discover",
            "model_registry",
            "discover_checkpoints",
            payload={
                "paths": [
                    CHECKPOINT_V1,
                    MISSING_CHECKPOINT,
                ],
            },
        )
    )

    eq(
        response.success,
        True,
        "discovery service succeeds",
    )

    eq(
        response.data[
            "count"
        ],
        2,
        "discovery count",
    )

    eq(
        response.data[
            "checkpoints"
        ][0][
            "valid"
        ],
        True,
        "discovery valid checkpoint",
    )

    eq(
        response.data[
            "checkpoints"
        ][1][
            "valid"
        ],
        False,
        "discovery invalid checkpoint",
    )


def test_errors():
    service = ModelRegistryService()

    missing = service.handle(
        ServiceRequest(
            "e1",
            "model_registry",
            "get_version",
            payload={
                "model_id": "missing",
                "version": "1",
            },
        )
    )

    eq(
        missing.error.code,
        "NOT_FOUND",
        "missing model version error",
    )

    wrong = service.handle(
        ServiceRequest(
            "e2",
            "training_service",
            "list_models",
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
            "model_registry",
            "register_checkpoint",
            payload={
                "model_id": "x",
                "version": "1",
                "checkpoint_path": MISSING_CHECKPOINT,
            },
        )
    )

    eq(
        invalid.error.code,
        "NOT_FOUND",
        "missing checkpoint registration rejected",
    )


def test_validation():
    expect_error(
        ValueError,
        lambda: ModelVersion(
            "",
            "1",
            "x",
            "abc",
            1,
            1,
        ),
        "empty model ID rejected",
    )

    state = {
        "format": "SireLLMModelRegistry",
        "version": 1,
        "models": [
            {
                "model_id": "x",
                "versions": [
                    ModelVersion(
                        "x",
                        "1",
                        "a",
                        "c1",
                        1,
                        1,
                        status="active",
                    ).to_dict(),
                    ModelVersion(
                        "x",
                        "2",
                        "b",
                        "c2",
                        1,
                        1,
                        status="active",
                    ).to_dict(),
                ],
            },
        ],
    }

    expect_error(
        ValueError,
        lambda: ModelRegistry().load_state(
            state
        ),
        "multiple active versions rejected on state load",
    )

    expect_error(
        TypeError,
        lambda: ModelRegistryService().handle(
            {}
        ),
        "non-ServiceRequest rejected",
    )


def main():
    (model_v1, info_v1), (
        model_v2,
        info_v2,
    ) = prepare()

    try:
        test_model_version_state()
        test_checkpoint_inspection(
            model_v1
        )
        test_discovery()
        test_register_and_list()
        test_promotion_and_deprecation()
        test_verify_unchanged()
        test_verify_corruption()
        test_registry_state_round_trip()
        test_protocol_safe_registry_state()
        test_service_end_to_end()
        test_service_protocol_round_trip()
        test_service_discovery()
        test_errors()
        test_validation()

    finally:
        cleanup()

    print(
        "MODEL REGISTRY TEST SUITE: PASS"
    )
    print(
        "Assertions passed:",
        ASSERTIONS,
    )
    print(
        "Files validated: 4/4"
    )
    print(
        "Real SireLLM checkpoint inspection: VALIDATED"
    )
    print(
        "Model/version registration: VALIDATED"
    )
    print(
        "Stage/promote/deprecate lifecycle: VALIDATED"
    )
    print(
        "Single-active-version invariant: VALIDATED"
    )
    print(
        "Checkpoint checksum/integrity verification: VALIDATED"
    )
    print(
        "Checkpoint discovery: VALIDATED"
    )
    print(
        "Registry state round-trip: VALIDATED"
    )
    print(
        "Protocol service operations: VALIDATED"
    )
    print(
        "Third-party dependencies: 0"
    )


main()
