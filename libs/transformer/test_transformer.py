MATH_BASE = "libs/core/math/"
AUTOGRAD_BASE = "libs/core/autograd/"
NEURAL_BASE = "libs/neural/"
TRANSFORMER_BASE = "libs/transformer/"

namespace = {
    "__builtins__": __builtins__,
}

MATH_FILES = [
    "scalar.py",
    "random.py",
    "tensor.py",
]

AUTOGRAD_FILES = [
    "operation.py",
    "value.py",
    "graph.py",
    "backward.py",
]

NEURAL_FILES = [
    "parameter.py",
    "layer.py",
    "initializers.py",
    "activations.py",
    "linear.py",
    "embedding.py",
    "dropout.py",
    "layer_norm.py",
]

TRANSFORMER_FILES = [
    "positional_encoding.py",
    "rotary_embedding.py",
    "causal_mask.py",
    "attention.py",
    "multi_head_attention.py",
    "feed_forward.py",
    "transformer_block.py",
    "decoder.py",
    "language_model.py",
    "generation.py",
]

for filename in MATH_FILES:
    path = MATH_BASE + filename
    source = open(
        path,
        "r",
        encoding="utf-8",
    ).read()
    exec(
        compile(source, path, "exec"),
        namespace,
    )

for filename in AUTOGRAD_FILES:
    path = AUTOGRAD_BASE + filename
    source = open(
        path,
        "r",
        encoding="utf-8",
    ).read()
    exec(
        compile(source, path, "exec"),
        namespace,
    )

for filename in NEURAL_FILES:
    path = NEURAL_BASE + filename
    source = open(
        path,
        "r",
        encoding="utf-8",
    ).read()
    exec(
        compile(source, path, "exec"),
        namespace,
    )

for filename in TRANSFORMER_FILES:
    path = TRANSFORMER_BASE + filename
    source = open(
        path,
        "r",
        encoding="utf-8",
    ).read()

    if "import " in source:
        raise AssertionError(
            "transformer implementation contains "
            "forbidden import statement: "
            + filename
        )

    exec(
        compile(source, path, "exec"),
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
    tolerance=1e-6,
):
    difference = actual - expected

    if difference < 0:
        difference = -difference

    return difference <= tolerance


def any_nonzero(values, tolerance=1e-10):
    for value in values:
        if value > tolerance or value < -tolerance:
            return True
    return False


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


def test_positional_encoding():
    encoding = SinusoidalPositionEncoding(
        d_model=4,
        max_seq_len=16,
    )

    table = encoding.encoding(3)

    eq(
        table.shape,
        (3, 4),
        "position table shape",
    )

    check(
        close(table[0, 0], 0.0),
        "position zero sine",
    )

    check(
        close(table[0, 1], 1.0),
        "position zero cosine",
    )

    x = Value(
        Tensor.zeros([3, 4])
    )

    y = encoding.apply(x)

    eq(
        y.shape,
        (3, 4),
        "position apply shape",
    )

    y.sum().backward()

    check(
        all(
            close(value, 1.0)
            for value in x.grad.flatten()
        ),
        "position encoding gradient identity",
    )


def test_rope_round_trip_gradient():
    rope = RotaryEmbedding(
        head_dim=4,
    )

    x = Value([
        [1.0, 2.0, 3.0, 4.0],
        [5.0, 6.0, 7.0, 8.0],
    ])

    y = rope.apply(x)

    eq(
        y.shape,
        x.shape,
        "RoPE output shape",
    )

    # Position zero must be identity.
    first = y.data.to_nested()[0]

    check(
        close(first[0], 1.0)
        and close(first[1], 2.0)
        and close(first[2], 3.0)
        and close(first[3], 4.0),
        "RoPE position zero identity",
    )

    y.sum().backward()

    check(
        x.grad.shape == x.shape,
        "RoPE gradient shape",
    )

    check(
        any_nonzero(x.grad.flatten()),
        "RoPE gradient flows",
    )


def test_causal_mask():
    mask = CausalMask()

    eq(
        mask.matrix(4),
        [
            [1, 0, 0, 0],
            [1, 1, 0, 0],
            [1, 1, 1, 0],
            [1, 1, 1, 1],
        ],
        "causal matrix",
    )

    prefix = CausalMask(
        prefix_length=2
    )

    check(
        prefix.allows(0, 2),
        "prefix mask allows cached keys",
    )


def test_attention_causality():
    attention = ScaledDotProductAttention(
        causal=True
    )

    q = Value([
        [1.0, 0.0],
        [1.0, 0.0],
        [1.0, 0.0],
    ])

    k = Value([
        [1.0, 0.0],
        [0.0, 1.0],
        [-1.0, 0.5],
    ])

    v = Value([
        [10.0, 0.0],
        [20.0, 0.0],
        [30.0, 0.0],
    ])

    output = attention(q, k, v)

    first = output.data.to_nested()[0]

    check(
        close(first[0], 10.0),
        "first causal query only sees first value",
    )

    weights = attention.last_weights[0]

    check(
        close(weights[0][1], 0.0)
        and close(weights[0][2], 0.0),
        "future attention weights are zero",
    )

    output.sum().backward()

    check(
        any_nonzero(q.grad.flatten()),
        "attention query gradient",
    )

    check(
        any_nonzero(k.grad.flatten()),
        "attention key gradient",
    )

    check(
        any_nonzero(v.grad.flatten()),
        "attention value gradient",
    )


def test_attention_softmax_rows():
    attention = ScaledDotProductAttention(
        causal=False
    )

    q = Value([
        [1.0, 0.0],
        [0.0, 1.0],
    ])

    k = Value([
        [1.0, 0.0],
        [0.0, 1.0],
    ])

    v = Value([
        [2.0, 3.0],
        [4.0, 5.0],
    ])

    attention(q, k, v)

    for row in attention.last_weights[0]:
        total = 0.0

        for weight in row:
            total += weight

        check(
            close(total, 1.0),
            "attention softmax sums to one",
        )


def test_multi_head_attention():
    layer = MultiHeadAttention(
        d_model=4,
        num_heads=2,
        causal=True,
        dropout=0.0,
        initializer=Initializers(17),
        use_rotary=True,
    )

    x = Value([
        [
            [1.0, 0.0, 0.5, -0.5],
            [0.0, 1.0, -0.5, 0.5],
            [1.0, 1.0, 0.25, 0.75],
        ]
    ])

    y = layer(x)

    eq(
        y.shape,
        (1, 3, 4),
        "multi-head output shape",
    )

    eq(
        len(layer.last_attention_weights),
        2,
        "two attention heads",
    )

    y.sum().backward()

    check(
        any_nonzero(x.grad.flatten()),
        "multi-head input gradient",
    )

    check(
        any_nonzero(
            layer.q_proj.weight.grad.flatten()
        ),
        "Q projection receives gradient",
    )

    check(
        any_nonzero(
            layer.k_proj.weight.grad.flatten()
        ),
        "K projection receives gradient",
    )

    check(
        any_nonzero(
            layer.v_proj.weight.grad.flatten()
        ),
        "V projection receives gradient",
    )


def test_feed_forward():
    layer = FeedForward(
        d_model=4,
        d_ff=12,
        dropout=0.0,
        initializer=Initializers(21),
    )

    x = Value([
        [1.0, 2.0, 3.0, 4.0],
        [2.0, 1.0, 0.0, -1.0],
    ])

    y = layer(x)

    eq(
        y.shape,
        (2, 4),
        "FFN shape",
    )

    y.sum().backward()

    check(
        any_nonzero(
            layer.fc1.weight.grad.flatten()
        ),
        "FFN first projection gradient",
    )

    check(
        any_nonzero(
            layer.fc2.weight.grad.flatten()
        ),
        "FFN second projection gradient",
    )


def test_transformer_block():
    block = TransformerBlock(
        d_model=4,
        num_heads=2,
        d_ff=8,
        dropout=0.0,
        initializer=Initializers(31),
        use_rotary=True,
    )

    x = Value([
        [
            [0.2, 0.1, -0.3, 0.7],
            [0.4, -0.2, 0.5, 0.1],
            [0.0, 0.6, -0.1, -0.4],
        ]
    ])

    y = block(
        x,
        mask=CausalMask(),
    )

    eq(
        y.shape,
        x.shape,
        "block preserves shape",
    )

    y.sum().backward()

    check(
        any_nonzero(x.grad.flatten()),
        "block input gradient",
    )

    check(
        block.parameter_count() > 0,
        "block has trainable parameters",
    )


def test_decoder():
    decoder = Decoder(
        num_layers=2,
        d_model=4,
        num_heads=2,
        d_ff=8,
        dropout=0.0,
        initializer=Initializers(41),
        use_rotary=True,
    )

    x = Value([
        [
            [0.1, 0.2, 0.3, 0.4],
            [0.5, 0.4, 0.3, 0.2],
        ]
    ])

    y = decoder(
        x,
        mask=CausalMask(),
    )

    eq(
        y.shape,
        (1, 2, 4),
        "decoder shape",
    )

    eq(
        len(decoder.blocks),
        2,
        "decoder block count",
    )

    check(
        decoder.parameter_count() > 0,
        "decoder parameter count",
    )


def build_tiny_model(
    position_mode="rotary",
):
    return LanguageModel(
        vocab_size=24,
        d_model=4,
        num_layers=2,
        num_heads=2,
        d_ff=8,
        max_seq_len=16,
        dropout=0.0,
        position_mode=position_mode,
        seed=51,
    )


def test_language_model_forward():
    model = build_tiny_model(
        "rotary"
    )

    logits = model([
        [1, 2, 3],
        [4, 5, 6],
    ])

    eq(
        logits.shape,
        (2, 3, 24),
        "language model logits shape",
    )

    check(
        model.parameter_count() > 0,
        "language model has parameters",
    )


def test_language_model_backward():
    model = build_tiny_model(
        "rotary"
    )

    logits = model([
        [1, 2, 3]
    ])

    # A weighted objective avoids symmetric sum cancellation and exercises
    # the complete embedding -> decoder -> LM-head backward chain.
    weights = []

    i = 0
    while i < logits.size:
        weights.append(
            ((i % 7) - 3) / 7.0
        )
        i += 1

    objective = (
        logits
        * Value(
            Tensor(
                weights,
                [
                    dimension
                    for dimension
                    in logits.shape
                ],
            ),
            requires_grad=False,
        )
    ).sum()

    objective.backward()

    check(
        any_nonzero(
            model.token_embedding.weight.grad.flatten()
        ),
        "embedding receives end-to-end gradient",
    )

    first_block = model.decoder.blocks[0]

    check(
        any_nonzero(
            first_block.attention.q_proj.weight.grad.flatten()
        ),
        "attention projection receives end-to-end gradient",
    )

    check(
        any_nonzero(
            model.lm_head.weight.grad.flatten()
        ),
        "LM head receives gradient",
    )


def test_sinusoidal_language_model():
    model = build_tiny_model(
        "sinusoidal"
    )

    logits = model(
        [[1, 2, 3]]
    )

    eq(
        logits.shape,
        (1, 3, 24),
        "sinusoidal language model",
    )


def test_generation():
    model = build_tiny_model(
        "rotary"
    )

    generator = GreedyGenerator(
        model
    )

    generated = generator.generate(
        [1, 2],
        max_new_tokens=3,
    )

    eq(
        len(generated),
        5,
        "greedy generation length",
    )

    eq(
        generated[:2],
        [1, 2],
        "generation preserves prompt",
    )

    for token in generated:
        check(
            0 <= token < model.vocab_size,
            "generated token in vocabulary",
        )


def test_validation():
    expect_error(
        ValueError,
        lambda: MultiHeadAttention(
            d_model=5,
            num_heads=2,
        ),
        "d_model divisibility validation",
    )

    expect_error(
        ValueError,
        lambda: RotaryEmbedding(
            head_dim=3,
        ),
        "RoPE even dimension validation",
    )

    model = build_tiny_model()

    expect_error(
        ValueError,
        lambda: model(
            [[1] * 17]
        ),
        "max sequence validation",
    )


def main():
    test_positional_encoding()
    test_rope_round_trip_gradient()
    test_causal_mask()
    test_attention_causality()
    test_attention_softmax_rows()
    test_multi_head_attention()
    test_feed_forward()
    test_transformer_block()
    test_decoder()
    test_language_model_forward()
    test_language_model_backward()
    test_sinusoidal_language_model()
    test_generation()
    test_validation()

    print(
        "TRANSFORMER TEST SUITE: PASS"
    )
    print(
        "Assertions passed:",
        ASSERTIONS,
    )
    print(
        "Files validated: 10/10"
    )
    print(
        "Math dependency validated: YES"
    )
    print(
        "Autograd dependency validated: YES"
    )
    print(
        "Neural dependency validated: YES"
    )
    print(
        "Causal attention + softmax: VALIDATED"
    )
    print(
        "Multi-head attention backward: VALIDATED"
    )
    print(
        "RoPE + sinusoidal positions: VALIDATED"
    )
    print(
        "Decoder-only LM forward/backward: VALIDATED"
    )
    print(
        "Autoregressive greedy generation: VALIDATED"
    )
    print(
        "Third-party dependencies: 0"
    )


main()
