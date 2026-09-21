MATH_BASE = "libs/core/math/"
AUTOGRAD_BASE = "libs/core/autograd/"
LOSSES_BASE = "libs/training/losses/"

namespace = {
    "__builtins__": __builtins__,
}

for filename in [
    "scalar.py",
    "tensor.py",
]:
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

for filename in [
    "operation.py",
    "value.py",
    "graph.py",
    "backward.py",
]:
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

for filename in [
    "softmax.py",
    "cross_entropy.py",
]:
    path = LOSSES_BASE + filename
    source = open(
        path,
        "r",
        encoding="utf-8",
    ).read()

    if "import " in source:
        raise AssertionError(
            "loss implementation contains forbidden import: "
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


def list_close(
    actual,
    expected,
    tolerance=1e-6,
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


def test_softmax_forward():
    softmax = Softmax()

    x = Value([
        [1.0, 2.0, 3.0],
        [1000.0, 1001.0, 1002.0],
    ])

    y = softmax(x)

    eq(
        y.shape,
        (2, 3),
        "softmax shape",
    )

    rows = y.data.to_nested()

    for row in rows:
        total = 0.0

        for value in row:
            total += value

        check(
            close(total, 1.0),
            "softmax rows sum to one",
        )

    check(
        list_close(
            rows[0],
            rows[1],
            tolerance=1e-10,
        ),
        "softmax numerically stable under constant shifts",
    )

    check(
        rows[0][2] > rows[0][1]
        and rows[0][1] > rows[0][0],
        "softmax ordering",
    )


def test_softmax_backward():
    softmax = Softmax()

    x = Value([
        [0.2, -0.1, 0.7]
    ])

    y = softmax(x)

    weights = Value(
        [[1.5, -0.25, 0.75]],
        requires_grad=False,
    )

    loss = (y * weights).sum()
    loss.backward()

    analytic = x.grad.flatten()

    epsilon = 1e-5
    numerical = []
    base = [0.2, -0.1, 0.7]

    i = 0

    while i < 3:
        plus = base[:]
        minus = base[:]

        plus[i] += epsilon
        minus[i] -= epsilon

        plus_y = softmax(
            Value(
                [plus],
                requires_grad=False,
            )
        ).data.flatten()

        minus_y = softmax(
            Value(
                [minus],
                requires_grad=False,
            )
        ).data.flatten()

        weights_flat = [
            1.5,
            -0.25,
            0.75,
        ]

        plus_loss = 0.0
        minus_loss = 0.0

        j = 0

        while j < 3:
            plus_loss += (
                plus_y[j]
                * weights_flat[j]
            )

            minus_loss += (
                minus_y[j]
                * weights_flat[j]
            )

            j += 1

        numerical.append(
            (
                plus_loss
                - minus_loss
            )
            / (2.0 * epsilon)
        )

        i += 1

    check(
        list_close(
            analytic,
            numerical,
            tolerance=5e-5,
        ),
        "softmax analytic gradient matches finite difference",
    )


def test_temperature():
    x = Value([
        [0.0, 1.0, 2.0]
    ])

    cold = Softmax(
        temperature=0.5
    )(x).data.flatten()

    hot = Softmax(
        temperature=2.0
    )(x).data.flatten()

    check(
        cold[2] > hot[2],
        "lower temperature sharpens distribution",
    )


def test_log_softmax():
    x = Value([
        [1.0, 2.0, 3.0]
    ])

    log_probs = LogSoftmax()(x)
    probs = Softmax()(x)

    log_values = log_probs.data.flatten()
    prob_values = probs.data.flatten()

    i = 0

    while i < 3:
        check(
            close(
                exp(log_values[i]),
                prob_values[i],
                tolerance=1e-7,
            ),
            "log-softmax exponent matches softmax",
        )

        i += 1

    log_probs.sum().backward()

    check(
        x.grad.shape == x.shape,
        "log-softmax gradient shape",
    )


def test_cross_entropy_known_value():
    logits = Value([
        [1.0, 2.0, 3.0]
    ])

    loss = CrossEntropyLoss(
        reduction="mean"
    )(
        logits,
        [2],
    )

    # -log(exp(3)/(exp(1)+exp(2)+exp(3)))
    expected = -log(
        exp(3.0)
        / (
            exp(1.0)
            + exp(2.0)
            + exp(3.0)
        )
    )

    check(
        close(
            loss.item(),
            expected,
            tolerance=1e-7,
        ),
        "cross entropy known value",
    )


def test_cross_entropy_shapes():
    loss_fn = CrossEntropyLoss(
        reduction="none"
    )

    logits = Value([
        [
            [1.0, 0.0, -1.0, 2.0],
            [0.5, 1.5, -0.5, 0.0],
            [2.0, 1.0, 0.0, -1.0],
        ],
        [
            [0.0, 0.0, 0.0, 0.0],
            [1.0, 3.0, 2.0, 0.0],
            [-1.0, 0.0, 1.0, 2.0],
        ],
    ])

    targets = [
        [3, 1, 0],
        [2, 1, 3],
    ]

    losses = loss_fn(
        logits,
        targets,
    )

    eq(
        losses.shape,
        (2, 3),
        "none reduction preserves target shape",
    )

    check(
        all(
            value > 0.0
            for value
            in losses.data.flatten()
        ),
        "all CE losses positive",
    )


def test_cross_entropy_gradient_formula():
    logits = Value([
        [1.0, 2.0, 3.0]
    ])

    loss = CrossEntropyLoss()(
        logits,
        [2],
    )

    loss.backward()

    probabilities = Softmax()(
        Value(
            [[1.0, 2.0, 3.0]],
            requires_grad=False,
        )
    ).data.flatten()

    expected = [
        probabilities[0],
        probabilities[1],
        probabilities[2] - 1.0,
    ]

    check(
        list_close(
            logits.grad.flatten(),
            expected,
            tolerance=1e-7,
        ),
        "CE gradient equals softmax minus one-hot",
    )


def test_cross_entropy_numeric_gradient():
    base = [
        0.4,
        -0.2,
        1.1,
        0.7,
    ]

    logits = Value([base])
    loss_fn = CrossEntropyLoss()

    loss = loss_fn(
        logits,
        [2],
    )

    loss.backward()

    analytic = logits.grad.flatten()
    numerical = []
    epsilon = 1e-5

    i = 0

    while i < 4:
        plus = base[:]
        minus = base[:]

        plus[i] += epsilon
        minus[i] -= epsilon

        plus_loss = loss_fn(
            Value(
                [plus],
                requires_grad=False,
            ),
            [2],
        ).item()

        minus_loss = loss_fn(
            Value(
                [minus],
                requires_grad=False,
            ),
            [2],
        ).item()

        numerical.append(
            (
                plus_loss
                - minus_loss
            )
            / (2.0 * epsilon)
        )

        i += 1

    check(
        list_close(
            analytic,
            numerical,
            tolerance=5e-5,
        ),
        "cross entropy gradient matches finite difference",
    )


def test_ignore_index():
    logits = Value([
        [2.0, 1.0, 0.0],
        [0.0, 1.0, 2.0],
        [1.0, 2.0, 0.0],
    ])

    loss = CrossEntropyLoss(
        reduction="mean",
        ignore_index=-100,
    )(
        logits,
        [
            0,
            -100,
            1,
        ],
    )

    loss.backward()

    gradient = logits.grad.to_nested()

    check(
        list_close(
            gradient[1],
            [0.0, 0.0, 0.0],
        ),
        "ignored target has zero gradient",
    )

    check(
        loss.item() > 0.0,
        "ignored-target mean still valid",
    )


def test_label_smoothing():
    logits = Value([
        [4.0, 1.0, -1.0]
    ])

    plain = CrossEntropyLoss(
        label_smoothing=0.0
    )(
        logits.detach(),
        [0],
    ).item()

    smoothed_logits = Value([
        [4.0, 1.0, -1.0]
    ])

    smoothed_loss = CrossEntropyLoss(
        label_smoothing=0.1
    )(
        smoothed_logits,
        [0],
    )

    check(
        smoothed_loss.item() > plain,
        "label smoothing penalizes overconfident target",
    )

    smoothed_loss.backward()

    gradient = smoothed_logits.grad.flatten()

    check(
        abs(
            gradient[0]
        )
        < 1.0,
        "smoothed target gradient bounded",
    )


def test_sum_mean_relation():
    logits1 = Value([
        [1.0, 2.0, 3.0],
        [3.0, 1.0, 0.0],
    ])

    logits2 = Value([
        [1.0, 2.0, 3.0],
        [3.0, 1.0, 0.0],
    ])

    targets = [2, 0]

    total = CrossEntropyLoss(
        reduction="sum"
    )(
        logits1,
        targets,
    ).item()

    mean = CrossEntropyLoss(
        reduction="mean"
    )(
        logits2,
        targets,
    ).item()

    check(
        close(
            total,
            mean * 2.0,
            tolerance=1e-8,
        ),
        "sum and mean reductions consistent",
    )


def test_rank_one_logits():
    logits = Value(
        [0.0, 1.0, 2.0]
    )

    loss = CrossEntropyLoss()(
        logits,
        2,
    )

    check(
        loss.item() > 0.0,
        "rank-one logits supported",
    )

    loss.backward()

    eq(
        logits.grad.shape,
        (3,),
        "rank-one gradient shape",
    )


def test_validation():
    expect_error(
        ValueError,
        lambda: Softmax(
            temperature=0.0
        ),
        "invalid temperature",
    )

    expect_error(
        ValueError,
        lambda: CrossEntropyLoss(
            reduction="bad"
        ),
        "invalid reduction",
    )

    expect_error(
        ValueError,
        lambda: CrossEntropyLoss(
            label_smoothing=1.0
        ),
        "invalid label smoothing",
    )

    expect_error(
        ValueError,
        lambda: CrossEntropyLoss()(
            Value([
                [1.0, 2.0],
                [2.0, 3.0],
            ]),
            [[0, 1]],
        ),
        "target shape mismatch",
    )

    expect_error(
        IndexError,
        lambda: CrossEntropyLoss()(
            Value([
                [1.0, 2.0, 3.0]
            ]),
            [4],
        ),
        "target out of range",
    )

    expect_error(
        ValueError,
        lambda: CrossEntropyLoss(
            ignore_index=-100
        )(
            Value([
                [1.0, 2.0, 3.0]
            ]),
            [-100],
        ),
        "mean requires active target",
    )


def main():
    test_softmax_forward()
    test_softmax_backward()
    test_temperature()
    test_log_softmax()
    test_cross_entropy_known_value()
    test_cross_entropy_shapes()
    test_cross_entropy_gradient_formula()
    test_cross_entropy_numeric_gradient()
    test_ignore_index()
    test_label_smoothing()
    test_sum_mean_relation()
    test_rank_one_logits()
    test_validation()

    print(
        "LOSSES TEST SUITE: PASS"
    )
    print(
        "Assertions passed:",
        ASSERTIONS,
    )
    print(
        "Files validated: 2/2"
    )
    print(
        "Stable Softmax/LogSoftmax: VALIDATED"
    )
    print(
        "CrossEntropy forward/backward: VALIDATED"
    )
    print(
        "Finite-difference gradients: VALIDATED"
    )
    print(
        "Ignore-index + label smoothing: VALIDATED"
    )
    print(
        "Language-model tensor shapes: VALIDATED"
    )
    print(
        "Third-party dependencies: 0"
    )


main()
