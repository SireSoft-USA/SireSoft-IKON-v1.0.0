PARSERS_BASE = "libs/data/parsers/"
REGISTRY_BASE = "services/model_registry/"
CONFIG_BASE = "configs/model_registry/"

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
        REGISTRY_BASE,
        [
            "model_version.py",
            "registry.py",
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
    "version.py",
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
            "model-registry config implementation contains forbidden import: "
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


class FakeInspector:
    def __init__(
        self,
    ):
        self.rows = {}
        self.invalid = {}

    def add(
        self,
        path,
        checksum,
        size,
        parameter_count,
        architecture=None,
        metadata=None,
    ):
        self.rows[
            path
        ] = {
            "path": path,
            "valid": True,
            "checksum": checksum,
            "bytes": size,
            "parameter_count": (
                parameter_count
            ),
            "architecture": (
                {}
                if architecture
                is None
                else architecture
            ),
            "metadata": (
                {}
                if metadata
                is None
                else metadata
            ),
        }

    def inspect(
        self,
        path,
    ):
        if path not in self.rows:
            raise FileNotFoundError(
                path
            )

        return dict(
            self.rows[
                path
            ]
        )

    def try_inspect(
        self,
        path,
    ):
        if path in self.invalid:
            return {
                "path": path,
                "valid": False,
                "error": (
                    "simulated invalid checkpoint"
                ),
            }

        try:
            return self.inspect(
                path
            )

        except Exception as error:
            return {
                "path": path,
                "valid": False,
                "error": str(
                    error
                ),
            }


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


def inspector():
    value = FakeInspector()

    value.add(
        "models/base-v1.ckpt",
        "aaa111",
        100,
        10,
        architecture={
            "layers": 2,
        },
        metadata={
            "trained_on": (
                "canonical-v1"
            ),
        },
    )

    value.add(
        "models/base-v2.ckpt",
        "bbb222",
        120,
        12,
        architecture={
            "layers": 3,
        },
        metadata={
            "trained_on": (
                "canonical-v2"
            ),
        },
    )

    value.add(
        "models/other-v1.ckpt",
        "ccc333",
        90,
        8,
    )

    return value


def sample_config():
    return ModelRegistryConfig(
        versions=[
            ModelVersionConfig(
                model_id="sirellm",
                version="1.0.0",
                checkpoint_path=(
                    "models/base-v1.ckpt"
                ),
                stage=True,
                verify=True,
                metadata={
                    "channel": "stable",
                },
            ),
            ModelVersionConfig(
                model_id="sirellm",
                version="2.0.0",
                checkpoint_path=(
                    "models/base-v2.ckpt"
                ),
                promote=True,
                verify=True,
                metadata={
                    "channel": "candidate",
                },
            ),
            ModelVersionConfig(
                model_id="other",
                version="1",
                checkpoint_path=(
                    "models/other-v1.ckpt"
                ),
                enabled=False,
            ),
        ],
    )


def test_version_config():
    item = ModelVersionConfig(
        "model",
        "v1",
        "model.ckpt",
        promote=True,
    )

    eq(
        item.stage,
        True,
        "promoted version is automatically staged",
    )

    eq(
        item.key(),
        "model@v1",
        "model version config key",
    )

    expect_error(
        ValueError,
        lambda: ModelVersionConfig(
            "m",
            "v",
            "x",
            promote=True,
            enabled=False,
        ),
        "disabled version cannot be promoted",
    )


def test_codec():
    text = (
        '{"versions":['
        '{"model_id":"sirellm","version":"1",'
        '"checkpoint_path":"m1.ckpt","stage":true},'
        '{"model_id":"sirellm","version":"2",'
        '"checkpoint_path":"m2.ckpt","promote":true,'
        '"metadata":{"source":"train-job-2"}}'
        '],'
        '"verify_all":true}'
    )

    config = (
        ModelRegistryConfigCodec()
        .decode_text(
            text
        )
    )

    eq(
        len(
            config.versions
        ),
        2,
        "codec version count",
    )

    eq(
        config.verify_all,
        True,
        "codec verify_all",
    )

    eq(
        config.versions[
            1
        ].metadata[
            "source"
        ],
        "train-job-2",
        "codec version metadata",
    )


def test_duplicate_rejected():
    expect_error(
        ValueError,
        lambda: ModelRegistryConfig(
            versions=[
                ModelVersionConfig(
                    "same",
                    "1",
                    "a.ckpt",
                ),
                ModelVersionConfig(
                    "same",
                    "1",
                    "b.ckpt",
                ),
            ],
        ),
        "duplicate model version config rejected",
    )


def test_validator_multiple_promotions():
    config = ModelRegistryConfig(
        versions=[
            ModelVersionConfig(
                "model",
                "1",
                "1.ckpt",
                promote=True,
            ),
            ModelVersionConfig(
                "model",
                "2",
                "2.ckpt",
                promote=True,
            ),
        ],
    )

    result = (
        ModelRegistryConfigValidator()
        .validate(
            config
        )
    )

    eq(
        result[
            "valid"
        ],
        False,
        "multiple configured promotions invalid",
    )

    eq(
        result[
            "errors"
        ][
            0
        ][
            "code"
        ],
        "MULTIPLE_PROMOTED_VERSIONS",
        "multiple promotions error code",
    )


def test_factory_registry():
    result = (
        ModelRegistryConfigFactory()
        .build_registry(
            sample_config(),
            inspector=(
                inspector()
            ),
        )
    )

    registry = result[
        "registry"
    ]

    eq(
        result[
            "registered_count"
        ],
        2,
        "disabled version excluded from startup registration",
    )

    eq(
        len(
            result[
                "verification"
            ]
        ),
        2,
        "per-version verification performed",
    )

    first = registry.get(
        "sirellm",
        "1.0.0",
    )

    second = registry.get(
        "sirellm",
        "2.0.0",
    )

    eq(
        first.status,
        "staged",
        "first configured version staged",
    )

    eq(
        second.status,
        "active",
        "promoted configured version active",
    )

    eq(
        registry.active(
            "sirellm"
        ).version,
        "2.0.0",
        "registry active lookup reflects config promotion",
    )

    eq(
        second.architecture[
            "layers"
        ],
        3,
        "registry preserves checkpoint architecture metadata",
    )

    eq(
        second.metadata[
            "trained_on"
        ],
        "canonical-v2",
        "registry preserves inspector checkpoint metadata",
    )

    eq(
        second.metadata[
            "channel"
        ],
        "candidate",
        "config metadata overlays checkpoint metadata",
    )

    eq(
        registry.contains(
            "other",
            "1",
        ),
        False,
        "disabled configured model is not registered",
    )


def test_verify_all():
    config = ModelRegistryConfig(
        versions=[
            ModelVersionConfig(
                "sirellm",
                "1",
                "models/base-v1.ckpt",
            ),
        ],
        verify_all=True,
    )

    result = (
        ModelRegistryConfigFactory()
        .build_registry(
            config,
            inspector=(
                inspector()
            ),
        )
    )

    eq(
        len(
            result[
                "verification"
            ]
        ),
        1,
        "verify_all verifies register-only version",
    )

    eq(
        result[
            "verification"
        ][
            0
        ][
            "valid"
        ],
        True,
        "verify_all successful verification",
    )


def test_failed_verification_modes():
    fake = inspector()

    fake.invalid[
        "models/base-v1.ckpt"
    ] = True

    strict = ModelRegistryConfig(
        versions=[
            ModelVersionConfig(
                "sirellm",
                "1",
                "models/base-v1.ckpt",
                verify=True,
            ),
        ],
        fail_on_verification_error=True,
    )

    expect_error(
        RuntimeError,
        lambda: (
            ModelRegistryConfigFactory()
            .build_registry(
                strict,
                inspector=fake,
            )
        ),
        "strict verification failure aborts registry bootstrap",
    )

    lenient = ModelRegistryConfig(
        versions=[
            ModelVersionConfig(
                "sirellm",
                "1",
                "models/base-v1.ckpt",
                verify=True,
            ),
        ],
        fail_on_verification_error=False,
    )

    result = (
        ModelRegistryConfigFactory()
        .build_registry(
            lenient,
            inspector=fake,
        )
    )

    eq(
        result[
            "verification"
        ][
            0
        ][
            "valid"
        ],
        False,
        "lenient bootstrap records failed verification",
    )


def test_export_state_after_bootstrap():
    registry = (
        ModelRegistryConfigFactory()
        .build_registry(
            sample_config(),
            inspector=(
                inspector()
            ),
        )[
            "registry"
        ]
    )

    state = registry.export_state()

    eq(
        state[
            "format"
        ],
        "SireLLMModelRegistry",
        "bootstrapped registry exports native state format",
    )

    eq(
        state[
            "models"
        ][
            0
        ][
            "model_id"
        ],
        "sirellm",
        "bootstrapped registry exports configured model",
    )


def main():
    test_version_config()
    test_codec()
    test_duplicate_rejected()
    test_validator_multiple_promotions()
    test_factory_registry()
    test_verify_all()
    test_failed_verification_modes()
    test_export_state_after_bootstrap()

    print(
        "MODEL REGISTRY CONFIG TEST SUITE: PASS"
    )
    print(
        "Assertions passed:",
        ASSERTIONS,
    )
    print(
        "Files validated: 5/5"
    )
    print(
        "Typed checkpoint bootstrap configuration: VALIDATED"
    )
    print(
        "Handwritten JSON decoding: VALIDATED"
    )
    print(
        "Promotion conflict validation: VALIDATED"
    )
    print(
        "ModelRegistry bootstrap generation: VALIDATED"
    )
    print(
        "Stage/promote lifecycle mapping: VALIDATED"
    )
    print(
        "Checkpoint metadata preservation: VALIDATED"
    )
    print(
        "Strict/lenient verification modes: VALIDATED"
    )
    print(
        "Disabled-version exclusion: VALIDATED"
    )
    print(
        "Third-party dependencies: 0"
    )


main()
