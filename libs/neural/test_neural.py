MATH_BASE = "libs/core/math/"
AUTOGRAD_BASE = "libs/core/autograd/"
NEURAL_BASE = "libs/neural/"

namespace = {"__builtins__": __builtins__}

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

for filename in MATH_FILES:
    path = MATH_BASE + filename
    source = open(path, "r", encoding="utf-8").read()
    exec(compile(source, path, "exec"), namespace)

for filename in AUTOGRAD_FILES:
    path = AUTOGRAD_BASE + filename
    source = open(path, "r", encoding="utf-8").read()
    exec(compile(source, path, "exec"), namespace)

for filename in NEURAL_FILES:
    path = NEURAL_BASE + filename
    source = open(path, "r", encoding="utf-8").read()

    if "import " in source:
        raise AssertionError(
            "neural implementation contains forbidden import statement: "
            + filename
        )

    exec(compile(source, path, "exec"), namespace)

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
        message + " | got=" + repr(actual) + " expected=" + repr(expected)
    )


def close(actual, expected, tolerance=1e-6):
    difference = actual - expected
    if difference < 0:
        difference = -difference
    return difference <= tolerance


def list_close(actual, expected, tolerance=1e-6):
    if len(actual) != len(expected):
        return False

    i = 0
    while i < len(actual):
        if not close(actual[i], expected[i], tolerance):
            return False
        i += 1

    return True


def expect_error(error_type, fn, message):
    global ASSERTIONS
    ASSERTIONS += 1

    try:
        fn()
    except error_type:
        return
    except Exception as exc:
        raise AssertionError(
            message + " | wrong exception=" + repr(exc)
        )

    raise AssertionError(
        message + " | expected exception was not raised"
    )


def test_parameter():
    p = Parameter([[1.0, 2.0], [3.0, 4.0]], "weight")

    eq(p.shape, (2, 2), "parameter shape")
    eq(p.element_count(), 4, "parameter element count")
    check(p.requires_grad, "parameter trainable")

    p.set_data(Tensor([[5.0, 6.0], [7.0, 8.0]]))
    eq(p.data[1, 1], 8.0, "parameter data replacement")

    expect_error(
        ValueError,
        lambda: p.set_data(Tensor([1.0, 2.0])),
        "parameter shape guard",
    )


def test_layer_registration():
    class PairLayer(Layer):
        def __init__(self):
            Layer.__init__(self)
            self.first = self.register_parameter(
                "first",
                Parameter([1.0, 2.0], "first"),
            )
            self.child = self.register_layer(
                "child",
                Linear(
                    2,
                    3,
                    initializer=Initializers(10),
                    name="child",
                ),
            )

        def forward(self, x):
            return self.child(x)

    layer = PairLayer()

    eq(len(layer.parameters()), 3, "recursive parameter count")
    eq(layer.parameter_count(), 11, "recursive scalar parameter count")

    names = [name for name, parameter in layer.named_parameters()]
    eq(
        names,
        ["first", "child.weight", "child.bias"],
        "named parameter hierarchy",
    )

    layer.eval()
    check(not layer.training, "parent eval")
    check(not layer.child.training, "child eval propagation")

    layer.train()
    check(layer.training, "parent train")
    check(layer.child.training, "child train propagation")


def test_initializers():
    first = Initializers(99)
    second = Initializers(99)

    a = first.xavier_uniform([4, 3])
    b = second.xavier_uniform([4, 3])

    eq(a.flatten(), b.flatten(), "initializer determinism")
    eq(a.shape, (4, 3), "initializer shape")
    eq(Initializers(1).zeros([2, 2]).sum(), 0.0, "zeros")
    eq(Initializers(1).ones([2, 2]).sum(), 4.0, "ones")


def test_linear_forward_backward():
    initializer = Initializers(7)
    layer = Linear(
        2,
        2,
        initializer=initializer,
        name="proj",
    )

    layer.weight.set_data(
        Tensor([
            [1.0, 2.0],
            [3.0, 4.0],
        ])
    )
    layer.bias.set_data(
        Tensor([0.5, -0.5])
    )

    x = Value([
        [1.0, 2.0],
        [3.0, 4.0],
    ])

    y = layer(x)

    check(
        list_close(
            y.data.flatten(),
            [7.5, 9.5, 15.5, 21.5],
        ),
        "linear forward",
    )

    y.sum().backward()

    check(
        list_close(
            x.grad.flatten(),
            [3.0, 7.0, 3.0, 7.0],
        ),
        "linear input gradient",
    )

    check(
        list_close(
            layer.weight.grad.flatten(),
            [4.0, 4.0, 6.0, 6.0],
        ),
        "linear weight gradient",
    )

    check(
        list_close(
            layer.bias.grad.flatten(),
            [2.0, 2.0],
        ),
        "linear bias gradient",
    )

    layer.zero_grad()

    check(
        list_close(
            layer.bias.grad.flatten(),
            [0.0, 0.0],
        ),
        "layer zero_grad",
    )


def test_linear_higher_rank():
    layer = Linear(
        2,
        3,
        initializer=Initializers(4),
    )

    x = Value([
        [
            [1.0, 2.0],
            [3.0, 4.0],
        ],
        [
            [5.0, 6.0],
            [7.0, 8.0],
        ],
    ])

    y = layer(x)

    eq(
        y.shape,
        (2, 2, 3),
        "linear projects final dimension",
    )

    y.sum().backward()

    eq(
        x.grad.shape,
        x.shape,
        "higher-rank linear gradient shape",
    )


def test_embedding():
    embedding = Embedding(
        5,
        3,
        initializer=Initializers(2),
        padding_idx=0,
    )

    embedding.weight.set_data(
        Tensor([
            [0.0, 0.0, 0.0],
            [1.0, 2.0, 3.0],
            [4.0, 5.0, 6.0],
            [7.0, 8.0, 9.0],
            [10.0, 11.0, 12.0],
        ])
    )

    out = embedding([[1, 2], [1, 0]])

    eq(
        out.shape,
        (2, 2, 3),
        "embedding output shape",
    )

    check(
        list_close(
            out.data.flatten(),
            [
                1.0, 2.0, 3.0,
                4.0, 5.0, 6.0,
                1.0, 2.0, 3.0,
                0.0, 0.0, 0.0,
            ],
        ),
        "embedding gather",
    )

    out.sum().backward()

    check(
        list_close(
            embedding.weight.grad.flatten(),
            [
                0.0, 0.0, 0.0,
                2.0, 2.0, 2.0,
                1.0, 1.0, 1.0,
                0.0, 0.0, 0.0,
                0.0, 0.0, 0.0,
            ],
        ),
        "embedding scatter-add gradient",
    )


def test_dropout():
    x = Value([1.0] * 100)

    dropout = Dropout(
        probability=0.5,
        seed=123,
    )

    train_output = dropout(x)
    values = train_output.data.flatten()

    zeros = 0
    scaled = 0

    for value in values:
        if close(value, 0.0):
            zeros += 1
        elif close(value, 2.0):
            scaled += 1
        else:
            raise AssertionError("dropout produced invalid scale")

    check(zeros > 0, "dropout removes elements")
    check(scaled > 0, "dropout keeps elements")

    dropout.eval()

    eval_output = dropout(x)

    check(
        eval_output is x,
        "eval dropout returns original Value",
    )


def test_activations():
    x = Value([-1.0, 0.0, 2.0])

    relu = ReLU()(x)
    check(
        list_close(relu.data.flatten(), [0.0, 0.0, 2.0]),
        "ReLU forward",
    )

    sigmoid = Sigmoid()(Value(0.0))
    check(close(sigmoid.item(), 0.5), "Sigmoid forward")

    tanh_value = Tanh()(Value(0.0))
    check(close(tanh_value.item(), 0.0), "Tanh forward")

    gelu_input = Value([0.0, 1.0])
    gelu_output = GELU()(gelu_input)

    check(close(gelu_output.data.flatten()[0], 0.0), "GELU zero")
    check(
        gelu_output.data.flatten()[1] > 0.8
        and gelu_output.data.flatten()[1] < 0.85,
        "GELU one",
    )

    gelu_output.sum().backward()

    check(
        gelu_input.grad.flatten()[1] > 1.0,
        "GELU gradient flows",
    )


def test_layer_norm_forward():
    layer = LayerNorm(
        3,
        epsilon=1e-5,
        affine=False,
    )

    x = Value([
        [1.0, 2.0, 3.0],
        [2.0, 4.0, 6.0],
    ])

    y = layer(x)

    eq(y.shape, (2, 3), "LayerNorm output shape")

    values = y.data.to_nested()

    row = 0
    while row < 2:
        mean = 0.0
        for value in values[row]:
            mean += value
        mean /= 3.0

        variance = 0.0
        for value in values[row]:
            variance += (value - mean) * (value - mean)
        variance /= 3.0

        check(close(mean, 0.0, 1e-6), "LayerNorm mean")
        check(close(variance, 1.0, 5e-5), "LayerNorm variance")
        row += 1


def test_layer_norm_backward():
    layer = LayerNorm(
        3,
        epsilon=1e-5,
        affine=True,
    )

    x = Value([
        [1.0, 2.0, 3.0],
        [4.0, 5.0, 8.0],
    ])

    y = layer(x)

    weighted = y * Value([
        [1.0, -2.0, 0.5],
        [0.25, 1.5, -1.0],
    ], requires_grad=False)

    weighted.sum().backward()

    check(
        x.grad.shape == x.shape,
        "LayerNorm input gradient shape",
    )

    check(
        layer.gamma.grad.shape == (3,),
        "LayerNorm gamma gradient shape",
    )

    check(
        layer.beta.grad.shape == (3,),
        "LayerNorm beta gradient shape",
    )

    check(
        any(
            not close(value, 0.0)
            for value in x.grad.flatten()
        ),
        "LayerNorm input gradient nonzero",
    )


def test_layer_norm_numeric_gradient():
    layer = LayerNorm(
        3,
        epsilon=1e-5,
        affine=False,
    )

    weights = Tensor([[1.0, -0.5, 2.0]])

    x = Value([[0.5, -1.0, 2.0]])
    y = layer(x)

    loss = (
        y
        * Value(weights, requires_grad=False)
    ).sum()

    loss.backward()

    analytic = x.grad.flatten()
    epsilon = 1e-5
    numerical = []

    base = [0.5, -1.0, 2.0]

    i = 0
    while i < 3:
        plus = base[:]
        minus = base[:]

        plus[i] += epsilon
        minus[i] -= epsilon

        plus_output = layer(
            Value([plus], requires_grad=False)
        ).data.flatten()

        minus_output = layer(
            Value([minus], requires_grad=False)
        ).data.flatten()

        plus_loss = 0.0
        minus_loss = 0.0

        j = 0
        weight_values = weights.flatten()

        while j < 3:
            plus_loss += plus_output[j] * weight_values[j]
            minus_loss += minus_output[j] * weight_values[j]
            j += 1

        numerical.append(
            (plus_loss - minus_loss)
            / (2.0 * epsilon)
        )

        i += 1

    check(
        list_close(
            analytic,
            numerical,
            tolerance=5e-4,
        ),
        "LayerNorm analytic gradient matches finite difference",
    )


def test_state_dict():
    layer = Linear(
        2,
        2,
        initializer=Initializers(3),
        name="state",
    )

    state = layer.state_dict()

    check("weight" in state, "state has weight")
    check("bias" in state, "state has bias")

    layer.weight.set_data(
        Tensor([
            [9.0, 9.0],
            [9.0, 9.0],
        ])
    )

    layer.load_state_dict(state)

    check(
        layer.weight.data.flatten()
        == state["weight"]["data"],
        "state restore",
    )


def main():
    test_parameter()
    test_layer_registration()
    test_initializers()
    test_linear_forward_backward()
    test_linear_higher_rank()
    test_embedding()
    test_dropout()
    test_activations()
    test_layer_norm_forward()
    test_layer_norm_backward()
    test_layer_norm_numeric_gradient()
    test_state_dict()

    print("NEURAL TEST SUITE: PASS")
    print("Assertions passed:", ASSERTIONS)
    print("Files validated: 8/8")
    print("Math dependency validated: YES")
    print("Autograd dependency validated: YES")
    print("Linear forward/backward: VALIDATED")
    print("Embedding gather/scatter gradient: VALIDATED")
    print("LayerNorm finite-difference gradient: VALIDATED")
    print("Train/eval + state handling: VALIDATED")
    print("Third-party dependencies: 0")


main()
