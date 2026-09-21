MATH_BASE = "libs/core/math/"
AUTOGRAD_BASE = "libs/core/autograd/"
NEURAL_BASE = "libs/neural/"
TRANSFORMER_BASE = "libs/transformer/"
INFERENCE_BASE = "libs/inference/"

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
    "logits_processor.py",
    "sampler.py",
    "generation_state.py",
    "kv_cache.py",
    "generator.py",
]:
    path = INFERENCE_BASE + filename

    source = open(
        path,
        "r",
        encoding="utf-8",
    ).read()

    if "import " in source:
        raise AssertionError(
            "inference implementation contains forbidden import: "
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
    tolerance=1e-8,
):
    difference = actual - expected

    if difference < 0:
        difference = -difference

    return difference <= tolerance


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


def active_ids(values):
    result = []

    index = 0

    while index < len(values):
        if values[index] > -5e29:
            result.append(index)

        index += 1

    return result


def build_model(seed=201):
    return LanguageModel(
        vocab_size=16,
        d_model=4,
        num_layers=1,
        num_heads=2,
        d_ff=8,
        max_seq_len=6,
        dropout=0.0,
        position_mode="rotary",
        seed=seed,
    )


def test_temperature():
    processor = LogitsProcessor(
        temperature=2.0
    )

    result = processor.process(
        [2.0, 4.0]
    )

    check(
        close(result[0], 1.0)
        and close(result[1], 2.0),
        "temperature scaling",
    )


def test_repetition_penalty():
    processor = LogitsProcessor(
        repetition_penalty=2.0
    )

    result = processor.process(
        [4.0, -2.0, 1.0],
        token_history=[0, 1, 0],
    )

    check(
        close(result[0], 2.0),
        "positive repeated logit penalized",
    )

    check(
        close(result[1], -4.0),
        "negative repeated logit penalized",
    )

    check(
        close(result[2], 1.0),
        "unseen logit unchanged",
    )


def test_top_k():
    processor = LogitsProcessor(
        top_k=2,
    )

    result = processor.process(
        [1.0, 5.0, 3.0, 4.0]
    )

    eq(
        active_ids(result),
        [1, 3],
        "top-k keeps highest logits",
    )


def test_top_p():
    processor = LogitsProcessor(
        top_p=0.70,
    )

    result = processor.process(
        [5.0, 4.0, 1.0, 0.0]
    )

    active = active_ids(result)

    check(
        0 in active,
        "top-p keeps most probable token",
    )

    check(
        len(active) >= 1
        and len(active) < 4,
        "top-p filters probability tail",
    )


def test_banned_tokens():
    processor = LogitsProcessor(
        banned_token_ids=[1, 3]
    )

    result = processor.process(
        [1.0, 2.0, 3.0, 4.0]
    )

    eq(
        active_ids(result),
        [0, 2],
        "banned token filtering",
    )


def test_greedy_sampler():
    sampler = GreedySampler()

    eq(
        sampler.sample(
            [1.0, 5.0, 5.0, 2.0]
        ),
        1,
        "greedy sampler stable tie break",
    )


def test_categorical_determinism():
    first = CategoricalSampler(
        seed=77
    )

    second = CategoricalSampler(
        seed=77
    )

    logits = [
        0.1,
        0.2,
        0.3,
    ]

    first_draws = []
    second_draws = []

    index = 0

    while index < 20:
        first_draws.append(
            first.sample(logits)
        )

        second_draws.append(
            second.sample(logits)
        )

        index += 1

    eq(
        first_draws,
        second_draws,
        "categorical sampling deterministic by seed",
    )

    check(
        all(
            0 <= value < 3
            for value in first_draws
        ),
        "categorical draws in range",
    )


def test_generation_state():
    state = GenerationState(
        prompt_ids=[1, 2],
        max_new_tokens=3,
        eos_token_ids=[9],
    )

    state.append(3)
    state.append(4)

    eq(
        state.all_ids(),
        [1, 2, 3, 4],
        "generation state token accumulation",
    )

    check(
        not state.finished,
        "generation state still active",
    )

    state.append(9)

    check(
        state.finished,
        "EOS finishes generation",
    )

    eq(
        state.stop_reason,
        "eos",
        "EOS stop reason",
    )


def test_generation_state_max_tokens():
    state = GenerationState(
        [1],
        max_new_tokens=2,
    )

    state.append(2)
    state.append(3)

    check(
        state.finished,
        "max tokens finishes generation",
    )

    eq(
        state.stop_reason,
        "max_new_tokens",
        "max-token stop reason",
    )


def test_kv_cache():
    cache = KVCache(
        num_layers=2,
        num_heads=2,
        head_dim=3,
        max_length=2,
    )

    layer = 0
    while layer < 2:
        head = 0

        while head < 2:
            cache.append(
                layer,
                head,
                [1.0, 2.0, 3.0],
                [4.0, 5.0, 6.0],
            )

            cache.append(
                layer,
                head,
                [7.0, 8.0, 9.0],
                [10.0, 11.0, 12.0],
            )

            cache.append(
                layer,
                head,
                [13.0, 14.0, 15.0],
                [16.0, 17.0, 18.0],
            )

            head += 1

        layer += 1

    eq(
        cache.common_length(),
        2,
        "KV cache max-length trimming",
    )

    eq(
        cache.layer(
            0,
            0,
        ).keys[0],
        [7.0, 8.0, 9.0],
        "KV cache trims oldest entry",
    )

    snapshot = cache.snapshot()

    eq(
        snapshot["num_layers"],
        2,
        "KV cache snapshot",
    )

    cache.clear()

    eq(
        cache.common_length(),
        0,
        "KV cache clear",
    )


def test_real_model_greedy_generation():
    model = build_model(
        seed=211
    )

    model.train()

    generator = InferenceGenerator(
        model=model,
        sampler=GreedySampler(),
        logits_processor=LogitsProcessor(
            temperature=1.0,
        ),
    )

    state = generator.generate(
        prompt_ids=[1, 2],
        max_new_tokens=3,
    )

    eq(
        len(state.generated_ids),
        3,
        "real Transformer generated requested tokens",
    )

    eq(
        len(state.all_ids()),
        5,
        "generated sequence length",
    )

    for token_id in state.generated_ids:
        check(
            0 <= token_id < model.vocab_size,
            "real generated token in vocabulary",
        )

    check(
        model.training,
        "generator restores original train mode",
    )


def test_real_model_context_window():
    model = build_model(
        seed=221
    )

    generator = InferenceGenerator(
        model=model,
        sampler=GreedySampler(),
        logits_processor=LogitsProcessor(),
        context_window=4,
    )

    # Total sequence will exceed context_window, but each model call is trimmed
    # to 4 tokens and therefore remains within model.max_seq_len.
    state = generator.generate(
        prompt_ids=[1, 2, 3, 4],
        max_new_tokens=4,
    )

    eq(
        len(state.all_ids()),
        8,
        "context-window generation retains full external history",
    )

    eq(
        state.stop_reason,
        "max_new_tokens",
        "context-window generation stop reason",
    )


def test_real_model_sampling():
    model = build_model(
        seed=231
    )

    first = InferenceGenerator(
        model=model,
        sampler=CategoricalSampler(
            seed=900
        ),
        logits_processor=LogitsProcessor(
            temperature=0.8,
            top_k=5,
            top_p=0.9,
            repetition_penalty=1.1,
        ),
        context_window=5,
    )

    second = InferenceGenerator(
        model=model,
        sampler=CategoricalSampler(
            seed=900
        ),
        logits_processor=LogitsProcessor(
            temperature=0.8,
            top_k=5,
            top_p=0.9,
            repetition_penalty=1.1,
        ),
        context_window=5,
    )

    a = first.generate(
        [1, 2],
        3,
    )

    b = second.generate(
        [1, 2],
        3,
    )

    eq(
        a.generated_ids,
        b.generated_ids,
        "real stochastic generation deterministic with same seed",
    )


def test_zero_generation():
    model = build_model(
        seed=241
    )

    state = InferenceGenerator(
        model
    ).generate(
        [1, 2],
        0,
    )

    eq(
        state.generated_ids,
        [],
        "zero-token generation",
    )

    eq(
        state.stop_reason,
        "max_new_tokens",
        "zero-token stop reason",
    )


def test_validation():
    expect_error(
        ValueError,
        lambda: LogitsProcessor(
            temperature=0.0
        ),
        "invalid temperature",
    )

    expect_error(
        ValueError,
        lambda: LogitsProcessor(
            top_p=1.1
        ),
        "invalid top-p",
    )

    expect_error(
        ValueError,
        lambda: KVCache(
            0,
            1,
            1,
        ),
        "invalid cache layers",
    )

    expect_error(
        ValueError,
        lambda: GenerationState(
            [],
            1,
        ),
        "empty prompt rejected",
    )


def main():
    test_temperature()
    test_repetition_penalty()
    test_top_k()
    test_top_p()
    test_banned_tokens()
    test_greedy_sampler()
    test_categorical_determinism()
    test_generation_state()
    test_generation_state_max_tokens()
    test_kv_cache()
    test_real_model_greedy_generation()
    test_real_model_context_window()
    test_real_model_sampling()
    test_zero_generation()
    test_validation()

    print(
        "INFERENCE TEST SUITE: PASS"
    )
    print(
        "Assertions passed:",
        ASSERTIONS,
    )
    print(
        "Files validated: 5/5"
    )
    print(
        "Temperature/top-k/top-p: VALIDATED"
    )
    print(
        "Repetition + banned-token controls: VALIDATED"
    )
    print(
        "Greedy + categorical sampling: VALIDATED"
    )
    print(
        "Real Transformer generation: VALIDATED"
    )
    print(
        "Context-window handling: VALIDATED"
    )
    print(
        "KV-cache storage primitive: VALIDATED"
    )
    print(
        "Third-party dependencies: 0"
    )


main()
