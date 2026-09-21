MATH_BASE = "libs/core/math/"
AUTOGRAD_BASE = "libs/core/autograd/"
NEURAL_BASE = "libs/neural/"
OPT_BASE = "libs/training/optimizers/"

namespace = {
    "__builtins__": __builtins__,
}

for filename in [
    "scalar.py",
    "random.py",
    "tensor.py",
]:
    path = MATH_BASE + filename
    source = open(path, "r", encoding="utf-8").read()
    exec(compile(source, path, "exec"), namespace)

for filename in [
    "operation.py",
    "value.py",
    "graph.py",
    "backward.py",
]:
    path = AUTOGRAD_BASE + filename
    source = open(path, "r", encoding="utf-8").read()
    exec(compile(source, path, "exec"), namespace)

for filename in [
    "parameter.py",
    "layer.py",
    "initializers.py",
    "linear.py",
]:
    path = NEURAL_BASE + filename
    source = open(path, "r", encoding="utf-8").read()
    exec(compile(source, path, "exec"), namespace)

for filename in [
    "sgd.py",
    "adamw.py",
]:
    path = OPT_BASE + filename
    source = open(path, "r", encoding="utf-8").read()

    if "import " in source:
        raise AssertionError(
            "optimizer implementation contains forbidden import: "
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
        message
        + " | got="
        + repr(actual)
        + " expected="
        + repr(expected)
    )


def close(actual, expected, tolerance=1e-7):
    difference = actual - expected

    if difference < 0:
        difference = -difference

    return difference <= tolerance


def list_close(actual, expected, tolerance=1e-7):
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
            message
            + " | wrong exception="
            + repr(exc)
        )

    raise AssertionError(
        message
        + " | expected exception was not raised"
    )


def set_grad(parameter, values):
    parameter.grad = Tensor(
        values,
        [dimension for dimension in parameter.shape],
    )


def test_sgd_basic():
    parameter = Parameter(
        [1.0, -2.0],
        "p",
    )

    set_grad(
        parameter,
        [0.5, -1.0],
    )

    optimizer = SGD(
        [parameter],
        learning_rate=0.1,
    )

    optimizer.step()

    check(
        list_close(
            parameter.data.flatten(),
            [0.95, -1.9],
        ),
        "SGD basic update",
    )

    eq(
        optimizer.step_count,
        1,
        "SGD step count",
    )


def test_sgd_momentum():
    parameter = Parameter(
        [1.0],
        "p",
    )

    optimizer = SGD(
        [parameter],
        learning_rate=0.1,
        momentum=0.9,
    )

    set_grad(parameter, [1.0])
    optimizer.step()

    check(
        close(
            parameter.data.flatten()[0],
            0.9,
        ),
        "SGD momentum first step",
    )

    set_grad(parameter, [1.0])
    optimizer.step()

    # v2 = 0.9 * 1 + 1 = 1.9
    # p2 = 0.9 - 0.1 * 1.9 = 0.71
    check(
        close(
            parameter.data.flatten()[0],
            0.71,
        ),
        "SGD momentum second step",
    )


def test_sgd_nesterov():
    parameter = Parameter(
        [1.0],
        "p",
    )

    set_grad(parameter, [1.0])

    optimizer = SGD(
        [parameter],
        learning_rate=0.1,
        momentum=0.9,
        nesterov=True,
    )

    optimizer.step()

    # v = 1, direction = grad + momentum*v = 1.9
    check(
        close(
            parameter.data.flatten()[0],
            0.81,
        ),
        "Nesterov update",
    )


def test_sgd_weight_decay():
    parameter = Parameter(
        [2.0],
        "p",
    )

    set_grad(parameter, [0.0])

    optimizer = SGD(
        [parameter],
        learning_rate=0.1,
        weight_decay=0.5,
    )

    optimizer.step()

    check(
        close(
            parameter.data.flatten()[0],
            1.9,
        ),
        "decoupled SGD weight decay",
    )


def test_zero_grad():
    parameter = Parameter(
        [1.0, 2.0],
        "p",
    )

    set_grad(
        parameter,
        [3.0, 4.0],
    )

    optimizer = SGD(
        [parameter],
        learning_rate=0.1,
    )

    optimizer.zero_grad()

    check(
        list_close(
            parameter.grad.flatten(),
            [0.0, 0.0],
        ),
        "optimizer zero_grad",
    )


def test_optimizer_accepts_layer():
    layer = Linear(
        2,
        3,
        initializer=Initializers(5),
    )

    optimizer = SGD(
        layer,
        learning_rate=0.01,
    )

    eq(
        len(optimizer.parameters),
        2,
        "optimizer collects layer parameters",
    )


def test_adamw_first_step():
    parameter = Parameter(
        [1.0, -1.0],
        "p",
    )

    set_grad(
        parameter,
        [0.5, -0.25],
    )

    optimizer = AdamW(
        [parameter],
        learning_rate=0.01,
        beta1=0.9,
        beta2=0.999,
        epsilon=1e-8,
        weight_decay=0.0,
    )

    optimizer.step()

    # On step 1 bias-corrected Adam update is approximately sign(gradient).
    values = parameter.data.flatten()

    check(
        close(
            values[0],
            0.99,
            tolerance=1e-6,
        ),
        "AdamW first positive-gradient step",
    )

    check(
        close(
            values[1],
            -0.99,
            tolerance=1e-6,
        ),
        "AdamW first negative-gradient step",
    )


def test_adamw_weight_decay():
    parameter = Parameter(
        [2.0],
        "p",
    )

    set_grad(parameter, [0.0])

    optimizer = AdamW(
        [parameter],
        learning_rate=0.1,
        weight_decay=0.2,
    )

    optimizer.step()

    check(
        close(
            parameter.data.flatten()[0],
            1.96,
            tolerance=1e-8,
        ),
        "AdamW decoupled weight decay",
    )


def test_adamw_grad_norm():
    first = Parameter([1.0], "a")
    second = Parameter([2.0], "b")

    set_grad(first, [3.0])
    set_grad(second, [4.0])

    optimizer = AdamW(
        [first, second],
        max_grad_norm=1.0,
        weight_decay=0.0,
    )

    check(
        close(
            optimizer.global_grad_norm(),
            5.0,
        ),
        "global gradient norm",
    )

    scale = optimizer._gradient_scale()

    check(
        close(
            scale,
            0.2,
        ),
        "gradient clipping scale",
    )


def test_adamw_moments_progress():
    parameter = Parameter(
        [1.0],
        "p",
    )

    optimizer = AdamW(
        [parameter],
        learning_rate=0.01,
        beta1=0.5,
        beta2=0.5,
        weight_decay=0.0,
    )

    set_grad(parameter, [2.0])
    optimizer.step()

    first_m1 = (
        optimizer
        ._first_moment[0]
        .flatten()[0]
    )

    first_m2 = (
        optimizer
        ._second_moment[0]
        .flatten()[0]
    )

    check(
        close(first_m1, 1.0),
        "Adam first moment step one",
    )

    check(
        close(first_m2, 2.0),
        "Adam second moment step one",
    )

    set_grad(parameter, [0.0])
    optimizer.step()

    second_m1 = (
        optimizer
        ._first_moment[0]
        .flatten()[0]
    )

    second_m2 = (
        optimizer
        ._second_moment[0]
        .flatten()[0]
    )

    check(
        close(second_m1, 0.5),
        "Adam first moment decay",
    )

    check(
        close(second_m2, 1.0),
        "Adam second moment decay",
    )


def test_sgd_state_round_trip():
    parameter = Parameter([1.0], "p")
    set_grad(parameter, [2.0])

    optimizer = SGD(
        [parameter],
        learning_rate=0.1,
        momentum=0.9,
    )

    optimizer.step()
    state = optimizer.state_dict()

    other_parameter = Parameter([5.0], "other")

    restored = SGD(
        [other_parameter],
        learning_rate=0.1,
        momentum=0.9,
    )

    restored.load_state_dict(state)

    eq(
        restored.step_count,
        1,
        "SGD state restores step count",
    )

    check(
        close(
            restored._velocity[0].flatten()[0],
            2.0,
        ),
        "SGD state restores momentum buffer",
    )


def test_adamw_state_round_trip():
    parameter = Parameter(
        [1.0, 2.0],
        "p",
    )

    set_grad(
        parameter,
        [0.5, -0.5],
    )

    optimizer = AdamW(
        [parameter],
        learning_rate=0.01,
        weight_decay=0.0,
    )

    optimizer.step()
    optimizer.step()

    state = optimizer.state_dict()

    other = Parameter(
        [9.0, 9.0],
        "other",
    )

    restored = AdamW(
        [other],
        learning_rate=0.01,
        weight_decay=0.0,
    )

    restored.load_state_dict(state)

    eq(
        restored.step_count,
        2,
        "AdamW state restores step count",
    )

    check(
        list_close(
            restored._first_moment[0].flatten(),
            optimizer._first_moment[0].flatten(),
        ),
        "AdamW first moment restored",
    )

    check(
        list_close(
            restored._second_moment[0].flatten(),
            optimizer._second_moment[0].flatten(),
        ),
        "AdamW second moment restored",
    )


def test_training_step_reduces_simple_loss():
    parameter = Parameter(
        [5.0],
        "x",
    )

    optimizer = SGD(
        [parameter],
        learning_rate=0.1,
    )

    before = (
        (parameter * parameter)
        .sum()
        .item()
    )

    optimizer.zero_grad()

    loss = (
        parameter
        * parameter
    ).sum()

    loss.backward()
    optimizer.step()

    after = (
        (parameter * parameter)
        .sum()
        .item()
    )

    check(
        after < before,
        "SGD step reduces simple quadratic loss",
    )


def test_validation():
    parameter = Parameter([1.0], "p")

    expect_error(
        ValueError,
        lambda: SGD(
            [parameter],
            learning_rate=0.0,
        ),
        "invalid SGD learning rate",
    )

    expect_error(
        ValueError,
        lambda: SGD(
            [parameter],
            momentum=0.0,
            nesterov=True,
        ),
        "Nesterov requires momentum",
    )

    expect_error(
        ValueError,
        lambda: AdamW(
            [parameter],
            beta1=1.0,
        ),
        "invalid beta1",
    )

    expect_error(
        ValueError,
        lambda: AdamW(
            [parameter],
            epsilon=0.0,
        ),
        "invalid epsilon",
    )

    expect_error(
        ValueError,
        lambda: AdamW(
            [],
        ),
        "empty parameter list rejected",
    )


def main():
    test_sgd_basic()
    test_sgd_momentum()
    test_sgd_nesterov()
    test_sgd_weight_decay()
    test_zero_grad()
    test_optimizer_accepts_layer()
    test_adamw_first_step()
    test_adamw_weight_decay()
    test_adamw_grad_norm()
    test_adamw_moments_progress()
    test_sgd_state_round_trip()
    test_adamw_state_round_trip()
    test_training_step_reduces_simple_loss()
    test_validation()

    print(
        "OPTIMIZERS TEST SUITE: PASS"
    )
    print(
        "Assertions passed:",
        ASSERTIONS,
    )
    print(
        "Files validated: 2/2"
    )
    print(
        "SGD + momentum + Nesterov: VALIDATED"
    )
    print(
        "AdamW moments + bias correction: VALIDATED"
    )
    print(
        "Decoupled weight decay: VALIDATED"
    )
    print(
        "Global gradient clipping: VALIDATED"
    )
    print(
        "Optimizer state round-trip: VALIDATED"
    )
    print(
        "Real autograd training step: VALIDATED"
    )
    print(
        "Third-party dependencies: 0"
    )


main()
