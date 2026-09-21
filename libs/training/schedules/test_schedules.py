MATH_BASE = "libs/core/math/"
AUTOGRAD_BASE = "libs/core/autograd/"
NEURAL_BASE = "libs/neural/"
OPT_BASE = "libs/training/optimizers/"
SCHEDULE_BASE = "libs/training/schedules/"

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
    exec(compile(source, path, "exec"), namespace)

for filename in [
    "constant.py",
    "warmup.py",
    "cosine.py",
]:
    path = SCHEDULE_BASE + filename
    source = open(path, "r", encoding="utf-8").read()

    if "import " in source:
        raise AssertionError(
            "schedule implementation contains forbidden import: "
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


def close(actual, expected, tolerance=1e-8):
    difference = actual - expected

    if difference < 0:
        difference = -difference

    return difference <= tolerance


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


def test_constant_schedule():
    schedule = ConstantSchedule(
        0.001
    )

    steps = [0, 1, 10, 100000]

    for step in steps:
        check(
            close(
                schedule.learning_rate(step),
                0.001,
            ),
            "constant schedule",
        )


def test_constant_optimizer_application():
    parameter = Parameter(
        [1.0],
        "p",
    )

    optimizer = SGD(
        [parameter],
        learning_rate=0.5,
    )

    schedule = ConstantSchedule(
        0.02
    )

    applied = schedule.apply(
        optimizer,
        7,
    )

    check(
        close(applied, 0.02),
        "constant apply return value",
    )

    check(
        close(
            optimizer.learning_rate,
            0.02,
        ),
        "constant changes real optimizer",
    )

    eq(
        schedule.last_step,
        7,
        "constant last step",
    )


def test_linear_warmup():
    schedule = LinearWarmupSchedule(
        target_learning_rate=0.1,
        warmup_steps=10,
        start_learning_rate=0.0,
    )

    check(
        close(
            schedule.learning_rate(0),
            0.0,
        ),
        "warmup step zero",
    )

    check(
        close(
            schedule.learning_rate(5),
            0.05,
        ),
        "warmup midpoint",
    )

    check(
        close(
            schedule.learning_rate(10),
            0.1,
        ),
        "warmup boundary",
    )

    check(
        close(
            schedule.learning_rate(100),
            0.1,
        ),
        "warmup post-boundary",
    )


def test_warmup_nonzero_start():
    schedule = LinearWarmupSchedule(
        target_learning_rate=0.1,
        warmup_steps=4,
        start_learning_rate=0.02,
    )

    check(
        close(
            schedule.learning_rate(2),
            0.06,
        ),
        "nonzero warmup start",
    )


def test_zero_length_warmup():
    schedule = LinearWarmupSchedule(
        target_learning_rate=0.1,
        warmup_steps=0,
    )

    check(
        close(
            schedule.learning_rate(0),
            0.1,
        ),
        "zero warmup immediately targets rate",
    )


def test_cosine_boundaries():
    schedule = CosineDecaySchedule(
        max_learning_rate=0.1,
        min_learning_rate=0.01,
        total_steps=100,
    )

    check(
        close(
            schedule.learning_rate(0),
            0.1,
            tolerance=1e-9,
        ),
        "cosine starts at max",
    )

    check(
        close(
            schedule.learning_rate(50),
            0.055,
            tolerance=1e-7,
        ),
        "cosine midpoint",
    )

    check(
        close(
            schedule.learning_rate(100),
            0.01,
            tolerance=1e-9,
        ),
        "cosine ends at min",
    )

    check(
        close(
            schedule.learning_rate(1000),
            0.01,
            tolerance=1e-9,
        ),
        "cosine clamps after end",
    )


def test_cosine_monotonic():
    schedule = CosineDecaySchedule(
        max_learning_rate=1.0,
        min_learning_rate=0.0,
        total_steps=50,
    )

    previous = schedule.learning_rate(0)

    step = 1

    while step <= 50:
        current = schedule.learning_rate(step)

        check(
            current <= previous + 1e-10,
            "cosine must not increase",
        )

        previous = current
        step += 1


def test_warmup_then_cosine():
    cosine = CosineDecaySchedule(
        max_learning_rate=0.1,
        min_learning_rate=0.01,
        total_steps=20,
    )

    schedule = WarmupThenSchedule(
        after_schedule=cosine,
        warmup_steps=4,
        start_learning_rate=0.0,
    )

    check(
        close(
            schedule.learning_rate(0),
            0.0,
        ),
        "composed warmup start",
    )

    check(
        close(
            schedule.learning_rate(2),
            0.05,
        ),
        "composed warmup midpoint",
    )

    check(
        close(
            schedule.learning_rate(4),
            0.1,
        ),
        "downstream starts exactly at warmup boundary",
    )

    check(
        schedule.learning_rate(5)
        < schedule.learning_rate(4),
        "cosine begins after warmup",
    )


def test_scheduler_drives_optimizer():
    parameter = Parameter(
        [1.0],
        "p",
    )

    parameter.grad = Tensor(
        [1.0],
        [1],
    )

    optimizer = SGD(
        [parameter],
        learning_rate=1.0,
    )

    schedule = LinearWarmupSchedule(
        target_learning_rate=0.1,
        warmup_steps=2,
        start_learning_rate=0.0,
    )

    schedule.apply(
        optimizer,
        1,
    )

    before = parameter.data.flatten()[0]

    optimizer.step()

    after = parameter.data.flatten()[0]

    check(
        close(
            optimizer.learning_rate,
            0.05,
        ),
        "warmup applied to optimizer",
    )

    check(
        close(
            before - after,
            0.05,
        ),
        "scheduled learning rate controls real optimizer update",
    )


def test_state_round_trip():
    original = CosineDecaySchedule(
        max_learning_rate=0.2,
        min_learning_rate=0.03,
        total_steps=500,
    )

    dummy = type(
        "Optimizer",
        (),
        {"learning_rate": 0.0},
    )()

    original.apply(
        dummy,
        77,
    )

    state = original.state_dict()

    restored = CosineDecaySchedule(
        max_learning_rate=1.0,
        min_learning_rate=0.0,
        total_steps=10,
    )

    restored.load_state_dict(
        state
    )

    check(
        close(
            restored.max_learning_rate,
            0.2,
        ),
        "state restores max rate",
    )

    check(
        close(
            restored.min_learning_rate,
            0.03,
        ),
        "state restores min rate",
    )

    eq(
        restored.total_steps,
        500,
        "state restores total steps",
    )

    eq(
        restored.last_step,
        77,
        "state restores last step",
    )


def test_resume_determinism():
    first = CosineDecaySchedule(
        0.3,
        total_steps=100,
        min_learning_rate=0.01,
    )

    state = first.state_dict()

    second = CosineDecaySchedule(
        1.0,
        total_steps=5,
    )

    second.load_state_dict(
        state
    )

    for step in [
        0,
        1,
        25,
        50,
        99,
        100,
    ]:
        check(
            close(
                first.learning_rate(step),
                second.learning_rate(step),
                tolerance=1e-10,
            ),
            "restored schedule deterministic",
        )


def test_validation():
    expect_error(
        ValueError,
        lambda: ConstantSchedule(
            -0.1
        ),
        "negative constant rate rejected",
    )

    expect_error(
        ValueError,
        lambda: LinearWarmupSchedule(
            0.1,
            -1,
        ),
        "negative warmup rejected",
    )

    expect_error(
        ValueError,
        lambda: CosineDecaySchedule(
            0.1,
            total_steps=0,
        ),
        "zero cosine steps rejected",
    )

    expect_error(
        ValueError,
        lambda: CosineDecaySchedule(
            0.01,
            total_steps=10,
            min_learning_rate=0.1,
        ),
        "min rate above max rejected",
    )

    expect_error(
        ValueError,
        lambda: ConstantSchedule(
            0.1
        ).learning_rate(-1),
        "negative step rejected",
    )


def main():
    test_constant_schedule()
    test_constant_optimizer_application()
    test_linear_warmup()
    test_warmup_nonzero_start()
    test_zero_length_warmup()
    test_cosine_boundaries()
    test_cosine_monotonic()
    test_warmup_then_cosine()
    test_scheduler_drives_optimizer()
    test_state_round_trip()
    test_resume_determinism()
    test_validation()

    print(
        "SCHEDULES TEST SUITE: PASS"
    )
    print(
        "Assertions passed:",
        ASSERTIONS,
    )
    print(
        "Files validated: 3/3"
    )
    print(
        "Constant learning rate: VALIDATED"
    )
    print(
        "Linear warmup: VALIDATED"
    )
    print(
        "Cosine decay: VALIDATED"
    )
    print(
        "Warmup + decay composition: VALIDATED"
    )
    print(
        "Real optimizer integration: VALIDATED"
    )
    print(
        "Checkpoint/resume state: VALIDATED"
    )
    print(
        "Third-party dependencies: 0"
    )


main()
