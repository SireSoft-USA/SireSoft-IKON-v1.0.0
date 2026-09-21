PARSERS_BASE = "libs/data/parsers/"
SECRET_BASE = "services/secret_service/"
CONFIG_BASE = "configs/secrets/"

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
        SECRET_BASE,
        [
            "sanitizer.py",
            "policy.py",
            "secret.py",
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
    "policy.py",
    "secret.py",
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
            "secrets config implementation contains forbidden import: "
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


class Clock:
    def __init__(
        self,
        value=100,
    ):
        self.value = value

    def now(
        self,
    ):
        current = self.value
        self.value += 1
        return current


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
        + repr(
            actual
        )
        + " expected="
        + repr(
            expected
        ),
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
            + repr(
                error
            )
        )

    raise AssertionError(
        message
        + " | expected exception was not raised"
    )


def sample_config():
    return SecretsConfig(
        secrets=[
            SecretDefinitionConfig(
                secret_id=(
                    "model-signing-key"
                ),
                policy=(
                    SecretPolicyConfig(
                        readers=[
                            "inference",
                        ],
                        writers=[
                            "operator",
                        ],
                        admins=[
                            "operator",
                        ],
                    )
                ),
                purpose=(
                    "model artifact verification"
                ),
                metadata={
                    "scope": "runtime",
                },
            ),
            SecretDefinitionConfig(
                secret_id=(
                    "disabled-key"
                ),
                policy=(
                    SecretPolicyConfig(
                        readers=[
                            "inference",
                        ],
                        admins=[
                            "operator",
                        ],
                    )
                ),
                enabled=False,
            ),
        ],
    )


def test_policy_config():
    policy = SecretPolicyConfig(
        readers=[
            "a",
            "a",
            "b",
        ],
        writers=[
            "operator",
        ],
        admins=[
            "admin",
        ],
    )

    eq(
        policy.readers,
        [
            "a",
            "b",
        ],
        "secret policy deduplicates principals",
    )


def test_definition_forbids_secret_metadata():
    expect_error(
        ValueError,
        lambda: (
            SecretDefinitionConfig(
                "bad",
                metadata={
                    "value": (
                        "do-not-store"
                    ),
                },
            )
        ),
        "secret value forbidden in config metadata",
    )

    expect_error(
        ValueError,
        lambda: (
            SecretDefinitionConfig(
                "nested-bad",
                metadata={
                    "nested": {
                        "password": (
                            "do-not-store"
                        ),
                    },
                },
            )
        ),
        "nested secret material forbidden in config metadata",
    )


def test_codec():
    text = (
        '{"secrets":['
        '{"secret_id":"model-signing-key",'
        '"purpose":"verification",'
        '"policy":{'
        '"readers":["inference"],'
        '"writers":["operator"],'
        '"admins":["operator"]'
        '},'
        '"metadata":{"scope":"runtime"}},'
        '{"secret_id":"optional-key",'
        '"enabled":false,'
        '"policy":{"admins":["operator"]}}'
        '],'
        '"attach_events":false,'
        '"attach_audit":false}'
    )

    config = (
        SecretsConfigCodec()
        .decode_text(
            text
        )
    )

    eq(
        len(
            config.secrets
        ),
        2,
        "codec secret definition count",
    )

    eq(
        config.secrets[
            0
        ].policy.readers,
        [
            "inference",
        ],
        "codec maps reader ACL",
    )

    public = config.to_dict()

    check(
        "value"
        not in public[
            "secrets"
        ][
            0
        ],
        "serialized secret config has no raw value field",
    )


def test_codec_rejects_raw_value():
    text = (
        '{"secrets":['
        '{"secret_id":"bad",'
        '"value":"plaintext",'
        '"policy":{"admins":["operator"]}}'
        ']}'
    )

    expect_error(
        ValueError,
        lambda: (
            SecretsConfigCodec()
            .decode_text(
                text
            )
        ),
        "codec rejects raw secret value",
    )


def test_validator():
    config = SecretsConfig(
        secrets=[
            SecretDefinitionConfig(
                "public-read",
                policy=(
                    SecretPolicyConfig(
                        readers=[
                            "*",
                        ],
                        admins=[
                            "operator",
                        ],
                    )
                ),
            ),
        ],
    )

    result = (
        SecretsConfigValidator()
        .validate(
            config
        )
    )

    eq(
        result[
            "valid"
        ],
        True,
        "wildcard reader is warning not structural failure",
    )

    warning_codes = [
        item[
            "code"
        ]
        for item
        in result[
            "warnings"
        ]
    ]

    check(
        "WILDCARD_READER"
        in warning_codes,
        "wildcard reader warning emitted",
    )

    bad = SecretsConfig(
        secrets=[
            SecretDefinitionConfig(
                "bad-admin",
                policy=(
                    SecretPolicyConfig(
                        admins=[
                            "*",
                        ],
                    )
                ),
            ),
        ],
    )

    bad_result = (
        SecretsConfigValidator()
        .validate(
            bad
        )
    )

    eq(
        bad_result[
            "valid"
        ],
        False,
        "wildcard secret admin forbidden",
    )


def test_factory_runtime_injection():
    config = sample_config()

    values = {
        "model-signing-key": (
            "runtime-secret-A"
        ),
        "disabled-key": (
            "runtime-secret-B"
        ),
    }

    clock = Clock()

    initialized = (
        SecretsConfigFactory()
        .initialize(
            config=config,
            value_provider=(
                lambda secret_id: (
                    values[
                        secret_id
                    ]
                )
            ),
            actor_id="operator",
            now_provider=(
                clock.now
            ),
        )
    )

    manager = initialized[
        "manager"
    ]

    eq(
        initialized[
            "count"
        ],
        2,
        "factory initializes every configured secret",
    )

    eq(
        manager.status()[
            "secret_count"
        ],
        2,
        "secret manager receives configured definitions",
    )

    resolved = manager.resolve_secret(
        "model-signing-key",
        actor_id="inference",
        now=200,
        purpose="verification",
    )

    eq(
        resolved,
        "runtime-secret-A",
        "runtime value provider injects secret material",
    )

    expect_error(
        PermissionError,
        lambda: manager.resolve_secret(
            "model-signing-key",
            actor_id="anonymous",
            now=201,
        ),
        "configured ACL denies unauthorized reader",
    )

    expect_error(
        RuntimeError,
        lambda: manager.resolve_secret(
            "disabled-key",
            actor_id="inference",
            now=202,
        ),
        "disabled configured secret cannot be resolved",
    )


def test_public_views_redacted():
    config = sample_config()

    initialized = (
        SecretsConfigFactory()
        .initialize(
            config,
            value_provider=(
                lambda secret_id: (
                    "super-secret-value"
                )
            ),
            actor_id="operator",
            now_provider=(
                Clock().now
            ),
        )
    )

    public = initialized[
        "manager"
    ].public_get(
        "model-signing-key"
    )

    eq(
        public[
            "versions"
        ][
            0
        ][
            "value"
        ],
        "[REDACTED]",
        "secret manager public view redacts raw value",
    )

    check(
        "super-secret-value"
        not in repr(
            public
        ),
        "secret value absent from public representation",
    )

    check(
        "super-secret-value"
        not in repr(
            config.to_dict()
        ),
        "secret value absent from config representation",
    )


def test_dependency_boundaries():
    events = SecretsConfig(
        secrets=[
            SecretDefinitionConfig(
                "event-secret",
                policy=(
                    SecretPolicyConfig(
                        admins=[
                            "operator",
                        ],
                    )
                ),
            ),
        ],
        attach_events=True,
    )

    expect_error(
        ValueError,
        lambda: (
            SecretsConfigFactory()
            .build_manager(
                events
            )
        ),
        "event dependency required when configured",
    )

    audit = SecretsConfig(
        secrets=[
            SecretDefinitionConfig(
                "audit-secret",
                policy=(
                    SecretPolicyConfig(
                        admins=[
                            "operator",
                        ],
                    )
                ),
            ),
        ],
        attach_audit=True,
    )

    expect_error(
        ValueError,
        lambda: (
            SecretsConfigFactory()
            .build_manager(
                audit
            )
        ),
        "audit dependency required when configured",
    )


def test_duplicate_secret_rejected():
    definition = (
        SecretDefinitionConfig(
            "same"
        )
    )

    expect_error(
        ValueError,
        lambda: SecretsConfig(
            secrets=[
                definition,
                definition,
            ],
        ),
        "duplicate secret id rejected",
    )


def main():
    test_policy_config()
    test_definition_forbids_secret_metadata()
    test_codec()
    test_codec_rejects_raw_value()
    test_validator()
    test_factory_runtime_injection()
    test_public_views_redacted()
    test_dependency_boundaries()
    test_duplicate_secret_rejected()

    print(
        "SECRETS CONFIG TEST SUITE: PASS"
    )
    print(
        "Assertions passed:",
        ASSERTIONS,
    )
    print(
        "Files validated: 6/6"
    )
    print(
        "Typed secret/ACL configuration: VALIDATED"
    )
    print(
        "Raw-secret/config separation: VALIDATED"
    )
    print(
        "Handwritten JSON decoding: VALIDATED"
    )
    print(
        "Wildcard-admin safety validation: VALIDATED"
    )
    print(
        "Runtime value-provider injection: VALIDATED"
    )
    print(
        "SecretManager ACL enforcement: VALIDATED"
    )
    print(
        "Disabled-secret behavior: VALIDATED"
    )
    print(
        "Public-value redaction: VALIDATED"
    )
    print(
        "Event/audit dependency boundaries: VALIDATED"
    )
    print(
        "Third-party dependencies: 0"
    )


main()
