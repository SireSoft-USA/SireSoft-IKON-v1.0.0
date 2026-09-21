PARSERS_BASE = "libs/data/parsers/"
SAFETY_BASE = "libs/safety/"
PROTOCOL_BASE = "libs/protocol/"
SERVICE_BASE = "services/guardrail_service/"
CONFIG_BASE = "configs/safety/"

namespace = {
    "__builtins__": __builtins__,
}

groups = [
    (
        PARSERS_BASE,
        [
            "json_parser.py",
        ],
    ),
    (
        SAFETY_BASE,
        [
            "decision.py",
            "patterns.py",
            "input_guard.py",
            "context_guard.py",
            "output_guard.py",
            "engine.py",
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
        SERVICE_BASE,
        [
            "public_view.py",
            "policy.py",
            "manager.py",
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
    "limits.py",
    "rule.py",
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
            "safety config implementation contains forbidden import: "
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
        + repr(expected),
    )


def expect_error(error_type, fn, message):
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
    return SafetyConfig(
        limits=SafetyLimitsConfig(
            input_characters=40,
            context_characters=200,
            output_characters=100,
        ),
        rules=[
            SafetyRuleConfig(
                phrase=(
                    "internal override phrase"
                ),
                code=(
                    "CUSTOM_OVERRIDE_PHRASE"
                ),
                category=(
                    "prompt_injection"
                ),
                severity=4,
            ),
            SafetyRuleConfig(
                phrase="secret_token=",
                code=(
                    "CUSTOM_SECRET_TOKEN"
                ),
                category=(
                    "secret_leakage"
                ),
                severity=4,
            ),
        ],
        replace_default_rules=False,
        metadata={
            "profile": "runtime",
        },
    )


def test_limits():
    limits = SafetyLimitsConfig(
        10,
        20,
        30,
    )

    eq(
        limits.input_characters,
        10,
        "input safety limit",
    )

    expect_error(
        ValueError,
        lambda: SafetyLimitsConfig(
            0,
            20,
            30,
        ),
        "zero safety limit rejected",
    )


def test_rule():
    rule = SafetyRuleConfig(
        "custom phrase",
        "CUSTOM_CODE",
        "prompt_injection",
        3,
    )

    eq(
        rule.severity,
        3,
        "custom safety severity",
    )

    expect_error(
        ValueError,
        lambda: SafetyRuleConfig(
            "x",
            "Y",
            "unknown",
            2,
        ),
        "unknown rule category rejected",
    )


def test_codec():
    text = (
        '{"limits":{'
        '"input_characters":80,'
        '"context_characters":800,'
        '"output_characters":120'
        '},'
        '"rules":['
        '{"phrase":"company-internal=",'
        '"code":"COMPANY_SECRET",'
        '"category":"secret_leakage",'
        '"severity":4}'
        '],'
        '"replace_default_rules":false,'
        '"metadata":{"profile":"prod"}'
        '}'
    )

    config = (
        SafetyConfigCodec()
        .decode_text(text)
    )

    eq(
        config.limits.context_characters,
        800,
        "codec context limit",
    )

    eq(
        config.rules[0].code,
        "COMPANY_SECRET",
        "codec custom rule",
    )

    eq(
        config.metadata["profile"],
        "prod",
        "codec metadata",
    )


def test_validator_duplicate_phrase():
    config = SafetyConfig(
        rules=[
            SafetyRuleConfig(
                "same phrase",
                "ONE",
                "secret_leakage",
                4,
            ),
            SafetyRuleConfig(
                "SAME PHRASE",
                "TWO",
                "secret_leakage",
                3,
            ),
        ],
    )

    result = (
        SafetyConfigValidator()
        .validate(config)
    )

    eq(
        result["valid"],
        False,
        "duplicate active phrase rejected",
    )

    eq(
        result["errors"][0]["code"],
        "DUPLICATE_RULE_PHRASE",
        "duplicate phrase error code",
    )


def test_factory_limits():
    manager = (
        SafetyConfigFactory()
        .build_manager(
            sample_config()
        )
    )

    too_long = manager.inspect_input(
        "x" * 41
    )

    eq(
        too_long["decision"]["action"],
        "block",
        "configured input character limit blocks oversized input",
    )

    eq(
        too_long["safe_input"],
        None,
        "blocked input is not forwarded",
    )


def test_custom_prompt_rule():
    manager = (
        SafetyConfigFactory()
        .build_manager(
            sample_config()
        )
    )

    result = manager.inspect_input(
        "internal override phrase"
    )

    eq(
        result["decision"]["action"],
        "warn",
        "custom prompt-injection rule warns on user input",
    )

    codes = [
        item["code"]
        for item
        in result["decision"]["findings"]
    ]

    check(
        "CUSTOM_OVERRIDE_PHRASE"
        in codes,
        "custom prompt rule finding emitted",
    )


def test_context_quarantine():
    manager = (
        SafetyConfigFactory()
        .build_manager(
            sample_config()
        )
    )

    text = (
        "Company profile.\n"
        "internal override phrase\n"
        "Normal product details.\n"
    )

    result = manager.inspect_context(
        text
    )

    eq(
        result["decision"]["action"],
        "sanitize",
        "configured context rule sanitizes untrusted instruction",
    )

    check(
        "[[UNTRUSTED_INSTRUCTION]]"
        in result["sanitized_context"],
        "context instruction quarantined",
    )


def test_custom_secret_output_block():
    manager = (
        SafetyConfigFactory()
        .build_manager(
            sample_config()
        )
    )

    result = manager.inspect_output(
        "debug secret_token=abc123"
    )

    eq(
        result["decision"]["action"],
        "block",
        "custom high-severity secret rule blocks output",
    )

    eq(
        result["safe_output"],
        None,
        "blocked secret output is not forwarded",
    )

    check(
        "abc123"
        not in repr(result),
        "blocked secret evidence is redacted from public result",
    )


def test_default_rules_preserved():
    manager = (
        SafetyConfigFactory()
        .build_manager(
            sample_config()
        )
    )

    result = manager.inspect_output(
        "authorization: bearer example-token"
    )

    eq(
        result["decision"]["action"],
        "block",
        "default secret leakage rules remain enabled",
    )


def test_replace_defaults():
    config = SafetyConfig(
        rules=[
            SafetyRuleConfig(
                "only-this-secret=",
                "ONLY_SECRET",
                "secret_leakage",
                4,
            ),
        ],
        replace_default_rules=True,
    )

    manager = (
        SafetyConfigFactory()
        .build_manager(config)
    )

    default_phrase = (
        manager.inspect_output(
            "authorization: bearer token"
        )
    )

    eq(
        default_phrase["decision"]["action"],
        "allow",
        "replace-default mode removes built-in phrase catalog",
    )

    custom = manager.inspect_output(
        "only-this-secret=abc"
    )

    eq(
        custom["decision"]["action"],
        "block",
        "replace-default mode retains configured custom rule",
    )


def test_service_creation():
    service = (
        SafetyConfigFactory()
        .build_service(
            sample_config()
        )
    )

    check(
        isinstance(
            service,
            GuardrailService,
        ),
        "factory creates GuardrailService",
    )

    response = service.handle(
        ServiceRequest(
            "safety-status",
            "guardrail_service",
            "status",
        )
    )

    eq(
        response.success,
        True,
        "configured guardrail service responds",
    )

    eq(
        response.data["status"]["ready"],
        True,
        "configured guardrail service ready",
    )

    policy = response.data[
        "status"
    ][
        "policy"
    ]

    eq(
        policy[
            "limits"
        ][
            "input_characters"
        ],
        40,
        "service exposes configured input limit",
    )


def test_audit_redaction():
    manager = (
        SafetyConfigFactory()
        .build_manager(
            sample_config()
        )
    )

    manager.inspect_output(
        "secret_token=very-sensitive"
    )

    audit = manager.audit_summary()

    eq(
        len(audit),
        1,
        "guardrail audit records configured decision",
    )

    check(
        "very-sensitive"
        not in repr(audit),
        "public audit excludes secret evidence",
    )


def main():
    test_limits()
    test_rule()
    test_codec()
    test_validator_duplicate_phrase()
    test_factory_limits()
    test_custom_prompt_rule()
    test_context_quarantine()
    test_custom_secret_output_block()
    test_default_rules_preserved()
    test_replace_defaults()
    test_service_creation()
    test_audit_redaction()

    print(
        "SAFETY CONFIG TEST SUITE: PASS"
    )
    print(
        "Assertions passed:",
        ASSERTIONS,
    )
    print(
        "Files validated: 6/6"
    )
    print(
        "Typed guardrail limits/rules configuration: VALIDATED"
    )
    print(
        "Handwritten JSON decoding: VALIDATED"
    )
    print(
        "Rule-catalog validation: VALIDATED"
    )
    print(
        "GuardrailEngine generation: VALIDATED"
    )
    print(
        "Custom prompt/secret rules: VALIDATED"
    )
    print(
        "Retrieved-context quarantine: VALIDATED"
    )
    print(
        "Output secret blocking/redaction: VALIDATED"
    )
    print(
        "GuardrailService generation: VALIDATED"
    )
    print(
        "Public audit redaction: VALIDATED"
    )
    print(
        "Third-party dependencies: 0"
    )


main()
