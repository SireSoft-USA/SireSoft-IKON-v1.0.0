SERIAL_BASE = "libs/core/serialization/"
PARSERS_BASE = "libs/data/parsers/"
FLAGS_BASE = "services/feature_flag_service/"
CONFIG_BASE = "configs/feature_flags/"

namespace = {
    "__builtins__": __builtins__,
}

groups = [
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
        FLAGS_BASE,
        [
            "rule.py",
            "flag.py",
            "evaluator.py",
            "persistence.py",
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
    "rule.py",
    "flag.py",
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
            "feature-flags config implementation contains forbidden import: "
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
    return FeatureFlagsConfig(
        flags=[
            FeatureFlagConfig(
                flag_key=(
                    "new_ranking"
                ),
                variants={
                    "off": False,
                    "on": True,
                },
                default_variant="off",
                disabled_variant="off",
                rules=[
                    FeatureFlagRuleConfig(
                        rule_id=(
                            "staff-on"
                        ),
                        conditions=[
                            {
                                "attribute": (
                                    "group"
                                ),
                                "operator": (
                                    "eq"
                                ),
                                "value": (
                                    "staff"
                                ),
                            },
                        ],
                        variant="on",
                    ),
                    FeatureFlagRuleConfig(
                        rule_id=(
                            "beta-rollout"
                        ),
                        conditions=[
                            {
                                "attribute": (
                                    "group"
                                ),
                                "operator": (
                                    "eq"
                                ),
                                "value": (
                                    "beta"
                                ),
                            },
                        ],
                        rollout_basis_points=(
                            2500
                        ),
                        rollout_variant="on",
                        salt="v1",
                    ),
                ],
            ),
            FeatureFlagConfig(
                flag_key=(
                    "guardrail_mode"
                ),
                variants={
                    "standard": (
                        "standard"
                    ),
                    "strict": (
                        "strict"
                    ),
                },
                default_variant=(
                    "standard"
                ),
                disabled_variant=(
                    "standard"
                ),
            ),
        ],
    )


def test_rule_config():
    rule = FeatureFlagRuleConfig(
        "r1",
        conditions=[
            {
                "attribute": (
                    "tier"
                ),
                "operator": (
                    "in"
                ),
                "value": [
                    "pro",
                    "admin",
                ],
            },
        ],
        variant="on",
    )

    eq(
        rule.conditions[
            0
        ][
            "operator"
        ],
        "in",
        "rule operator stored",
    )

    expect_error(
        ValueError,
        lambda: (
            FeatureFlagRuleConfig(
                "bad",
                variant="on",
                rollout_basis_points=100,
                rollout_variant="on",
            )
        ),
        "fixed and rollout variant cannot coexist",
    )


def test_flag_validation():
    expect_error(
        ValueError,
        lambda: FeatureFlagConfig(
            "bad",
            {
                "off": False,
            },
            default_variant=(
                "missing"
            ),
            disabled_variant="off",
        ),
        "missing default variant rejected",
    )

    expect_error(
        ValueError,
        lambda: FeatureFlagConfig(
            "bad-rule",
            {
                "off": False,
                "on": True,
            },
            default_variant="off",
            disabled_variant="off",
            rules=[
                FeatureFlagRuleConfig(
                    "r1",
                    variant="missing",
                ),
            ],
        ),
        "rule variant outside flag variants rejected",
    )


def test_codec():
    text = (
        '{"flags":['
        '{"flag_key":"new_ui",'
        '"variants":{"old":"old","new":"new"},'
        '"default_variant":"old",'
        '"disabled_variant":"old",'
        '"rules":['
        '{"rule_id":"staff","conditions":['
        '{"attribute":"group","operator":"eq","value":"staff"}'
        '],"variant":"new"}'
        ']},'
        '{"flag_key":"disabled_flag",'
        '"variants":{"off":false,"on":true},'
        '"default_variant":"on",'
        '"disabled_variant":"off",'
        '"enabled":false}'
        '],'
        '"persistence_path":"state/flags.bin"}'
    )

    config = (
        FeatureFlagsConfigCodec()
        .decode_text(
            text
        )
    )

    eq(
        len(
            config.flags
        ),
        2,
        "codec flag count",
    )

    eq(
        config.flags[
            0
        ].rules[
            0
        ].variant,
        "new",
        "codec fixed rule variant",
    )

    eq(
        config.persistence_path,
        "state/flags.bin",
        "codec persistence path",
    )


def test_duplicate_flag_rejected():
    flag = FeatureFlagConfig(
        "same",
        {
            "off": False,
            "on": True,
        },
        "off",
        "off",
    )

    expect_error(
        ValueError,
        lambda: FeatureFlagsConfig(
            flags=[
                flag,
                flag,
            ],
        ),
        "duplicate flag key rejected",
    )


def test_validator():
    config = FeatureFlagsConfig(
        flags=[
            FeatureFlagConfig(
                "single",
                {
                    "only": True,
                },
                "only",
                "only",
            ),
            FeatureFlagConfig(
                "rollout",
                {
                    "off": False,
                    "on": True,
                },
                "off",
                "off",
                rules=[
                    FeatureFlagRuleConfig(
                        "full",
                        rollout_basis_points=(
                            10000
                        ),
                        rollout_variant="on",
                    ),
                ],
            ),
        ],
    )

    result = (
        FeatureFlagsConfigValidator()
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
        "SINGLE_VARIANT_FLAG"
        in codes,
        "single variant warned",
    )

    check(
        "FULL_PERCENT_ROLLOUT"
        in codes,
        "full rollout warned",
    )


def test_factory_manager():
    manager = (
        FeatureFlagsConfigFactory()
        .build_manager(
            sample_config()
        )
    )

    eq(
        manager.status()[
            "flag_count"
        ],
        2,
        "factory creates configured flags",
    )

    eq(
        manager.status()[
            "rule_count"
        ],
        2,
        "factory creates configured rules",
    )

    staff = manager.evaluate(
        "new_ranking",
        "user-1",
        attributes={
            "group": "staff",
        },
    )

    eq(
        staff[
            "variant"
        ],
        "on",
        "fixed targeting rule selected",
    )

    eq(
        staff[
            "reason"
        ],
        "rule_match",
        "fixed targeting reason",
    )

    normal = manager.evaluate(
        "new_ranking",
        "user-2",
        attributes={
            "group": "regular",
        },
    )

    eq(
        normal[
            "variant"
        ],
        "off",
        "default variant selected for unmatched subject",
    )


def test_rollout_deterministic():
    manager = (
        FeatureFlagsConfigFactory()
        .build_manager(
            sample_config()
        )
    )

    first = manager.evaluate(
        "new_ranking",
        "stable-subject",
        attributes={
            "group": "beta",
        },
    )

    second = manager.evaluate(
        "new_ranking",
        "stable-subject",
        attributes={
            "group": "beta",
        },
    )

    eq(
        first[
            "variant"
        ],
        second[
            "variant"
        ],
        "rollout variant deterministic for same subject",
    )

    eq(
        first[
            "rollout_bucket"
        ],
        second[
            "rollout_bucket"
        ],
        "rollout bucket deterministic for same subject",
    )


def test_disabled_flag():
    config = FeatureFlagsConfig(
        flags=[
            FeatureFlagConfig(
                "off-switch",
                {
                    "off": False,
                    "on": True,
                },
                default_variant="on",
                disabled_variant="off",
                enabled=False,
            ),
        ],
    )

    manager = (
        FeatureFlagsConfigFactory()
        .build_manager(
            config
        )
    )

    result = manager.evaluate(
        "off-switch",
        "user",
    )

    eq(
        result[
            "variant"
        ],
        "off",
        "disabled flag uses disabled variant",
    )

    eq(
        result[
            "reason"
        ],
        "flag_disabled",
        "disabled flag reason",
    )


def test_event_dependency():
    config = FeatureFlagsConfig(
        flags=[
            FeatureFlagConfig(
                "flag",
                {
                    "off": False,
                    "on": True,
                },
                "off",
                "off",
            ),
        ],
        publish_events=True,
    )

    expect_error(
        ValueError,
        lambda: (
            FeatureFlagsConfigFactory()
            .build_manager(
                config
            )
        ),
        "event bus required when publish_events configured",
    )


def main():
    test_rule_config()
    test_flag_validation()
    test_codec()
    test_duplicate_flag_rejected()
    test_validator()
    test_factory_manager()
    test_rollout_deterministic()
    test_disabled_flag()
    test_event_dependency()

    print(
        "FEATURE FLAGS CONFIG TEST SUITE: PASS"
    )
    print(
        "Assertions passed:",
        ASSERTIONS,
    )
    print(
        "Files validated: 6/6"
    )
    print(
        "Typed feature flag/rule configuration: VALIDATED"
    )
    print(
        "Handwritten JSON decoding: VALIDATED"
    )
    print(
        "Variant/rule integrity validation: VALIDATED"
    )
    print(
        "FeatureFlagManager generation: VALIDATED"
    )
    print(
        "Fixed targeting-rule evaluation: VALIDATED"
    )
    print(
        "Deterministic rollout evaluation: VALIDATED"
    )
    print(
        "Disabled-variant behavior: VALIDATED"
    )
    print(
        "Event-bus dependency boundary: VALIDATED"
    )
    print(
        "Third-party dependencies: 0"
    )


main()
