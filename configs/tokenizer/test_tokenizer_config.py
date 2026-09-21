import os

SERIAL_BASE = "libs/core/serialization/"
PARSER_BASE = "libs/data/parsers/"
TOKENIZER_BASE = "libs/nlp/tokenizer/"
PROTOCOL_BASE = "libs/protocol/"
SERVICE_BASE = "services/tokenizer_service/"
CONFIG_BASE = "configs/tokenizer/"

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
        PARSER_BASE,
        [
            "json_parser.py",
        ],
    ),
    (
        TOKENIZER_BASE,
        [
            "special_tokens.py",
            "byte_encoder.py",
            "pair_counter.py",
            "vocabulary.py",
            "bpe_trainer.py",
            "bpe_tokenizer.py",
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
            "artifact.py",
            "state_codec.py",
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
    "training.py",
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
            "tokenizer config implementation contains forbidden import: "
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
ARTIFACT_PATH = (
    "configs/tokenizer/"
    "_test_tokenizer.sllmtok"
)


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


def cleanup():
    if os.path.isfile(
        ARTIFACT_PATH
    ):
        os.remove(
            ARTIFACT_PATH
        )


def corpus():
    return [
        (
            "SireSoft builds professional "
            "software engineering systems."
        ),
        (
            "SireSoft provides custom web "
            "and mobile application development."
        ),
        (
            "Artificial intelligence and machine "
            "learning support software automation."
        ),
        (
            "User asks a question and assistant "
            "answers using retrieved context."
        ),
        (
            "Software software software "
            "engineering engineering."
        ),
    ]


def training_config():
    return TokenizerConfig(
        mode="train",
        training=(
            TokenizerTrainingConfig(
                vocab_size=300,
                min_frequency=2,
            )
        ),
        artifact_path=(
            ARTIFACT_PATH
        ),
        persist_after_train=True,
        metadata={
            "profile": "sirellm",
        },
    )


def test_training_config():
    config = TokenizerTrainingConfig(
        vocab_size=300,
        min_frequency=2,
    )

    eq(
        config.vocab_size,
        300,
        "training vocab size",
    )

    eq(
        config.effective_special_tokens(),
        list(
            SpecialTokens.DEFAULTS
        ),
        "default special-token registry preserved",
    )

    expect_error(
        ValueError,
        lambda: TokenizerTrainingConfig(
            vocab_size=255
        ),
        "sub-byte vocabulary target rejected",
    )


def test_custom_special_validation():
    config = TokenizerConfig(
        mode="none",
        training=(
            TokenizerTrainingConfig(
                vocab_size=260,
                special_tokens=[
                    "<CUSTOM>",
                ],
            )
        ),
    )

    result = (
        TokenizerConfigValidator()
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
        "MISSING_RUNTIME_SPECIAL_TOKEN"
        in codes,
        "missing runtime special tokens warned",
    )


def test_codec():
    text = (
        '{"mode":"train",'
        '"training":{'
        '"vocab_size":300,'
        '"min_frequency":3,'
        '"special_tokens":['
        '"<BOS>","<EOS>","<PAD>","<UNK>"'
        ']},'
        '"artifact_path":"tokenizer.bin",'
        '"persist_after_train":true,'
        '"metadata":{"profile":"prod"}'
        '}'
    )

    config = (
        TokenizerConfigCodec()
        .decode_text(
            text
        )
    )

    eq(
        config.mode,
        "train",
        "codec tokenizer mode",
    )

    eq(
        config.training.min_frequency,
        3,
        "codec minimum pair frequency",
    )

    eq(
        config.persist_after_train,
        True,
        "codec persistence setting",
    )


def test_train_and_persist():
    result = (
        TokenizerConfigFactory()
        .initialize(
            training_config(),
            corpus=corpus(),
        )
    )

    manager = result[
        "manager"
    ]

    eq(
        manager.ready(),
        True,
        "configured tokenizer trains successfully",
    )

    check(
        manager.info()[
            "vocabulary_size"
        ] >= 256,
        "trained tokenizer preserves byte vocabulary",
    )

    check(
        manager.info()[
            "merge_count"
        ] > 0,
        "configured corpus learns real BPE merges",
    )

    check(
        os.path.isfile(
            ARTIFACT_PATH
        ),
        "configured tokenizer artifact persisted",
    )

    check(
        result[
            "artifact"
        ][
            "bytes"
        ] > 0,
        "persisted tokenizer artifact is non-empty",
    )


def test_round_trip_load():
    first = (
        TokenizerConfigFactory()
        .initialize(
            training_config(),
            corpus=corpus(),
        )[
            "manager"
        ]
    )

    text = (
        "SireSoft software engineering"
    )

    first_ids = first.encode(
        text,
        add_bos=True,
        add_eos=True,
    )

    loaded_config = TokenizerConfig(
        mode="load",
        artifact_path=(
            ARTIFACT_PATH
        ),
    )

    second = (
        TokenizerConfigFactory()
        .initialize(
            loaded_config
        )[
            "manager"
        ]
    )

    second_ids = second.encode(
        text,
        add_bos=True,
        add_eos=True,
    )

    eq(
        second_ids,
        first_ids,
        "loaded tokenizer reproduces exact encoding",
    )

    eq(
        second.decode(
            second_ids
        ),
        (
            "<BOS>"
            + text
            + "<EOS>"
        ),
        "loaded tokenizer reproduces exact decoding",
    )

    eq(
        second.export_state(),
        first.export_state(),
        "tokenizer artifact round trip preserves state exactly",
    )


def test_deterministic_training():
    factory = (
        TokenizerConfigFactory()
    )

    config = TokenizerConfig(
        mode="train",
        training=(
            TokenizerTrainingConfig(
                vocab_size=300,
                min_frequency=2,
            )
        ),
    )

    first = factory.initialize(
        config,
        corpus=corpus(),
    )[
        "manager"
    ]

    second = factory.initialize(
        config,
        corpus_provider=corpus,
    )[
        "manager"
    ]

    eq(
        first.export_state(),
        second.export_state(),
        "same corpus/config produces deterministic tokenizer state",
    )


def test_special_token_encoding():
    manager = (
        TokenizerConfigFactory()
        .initialize(
            TokenizerConfig(
                mode="train",
                training=(
                    TokenizerTrainingConfig(
                        vocab_size=280,
                        min_frequency=2,
                    )
                ),
            ),
            corpus=corpus(),
        )[
            "manager"
        ]
    )

    ids = manager.encode(
        "<USER>Hello<ASSISTANT>",
        allow_special=True,
    )

    check(
        len(
            ids
        ) >= 3,
        "configured tokenizer encodes special-token text",
    )

    decoded = manager.decode(
        ids
    )

    eq(
        decoded,
        "<USER>Hello<ASSISTANT>",
        "special-token encode/decode round trip",
    )


def test_none_mode():
    result = (
        TokenizerConfigFactory()
        .initialize(
            TokenizerConfig(
                mode="none"
            )
        )
    )

    eq(
        result[
            "manager"
        ].ready(),
        False,
        "none mode leaves tokenizer uninitialized",
    )

    eq(
        result[
            "info"
        ][
            "vocabulary_size"
        ],
        0,
        "none mode exposes empty tokenizer info",
    )


def test_train_requires_corpus():
    expect_error(
        ValueError,
        lambda: (
            TokenizerConfigFactory()
            .initialize(
                TokenizerConfig(
                    mode="train"
                )
            )
        ),
        "train mode requires runtime corpus",
    )


def test_service_creation():
    service = (
        TokenizerConfigFactory()
        .build_service(
            TokenizerConfig(
                mode="train",
                training=(
                    TokenizerTrainingConfig(
                        vocab_size=280,
                        min_frequency=2,
                    )
                ),
            ),
            corpus=corpus(),
        )
    )

    check(
        isinstance(
            service,
            TokenizerService,
        ),
        "factory creates TokenizerService",
    )

    response = service.handle(
        ServiceRequest(
            "tok-info",
            "tokenizer_service",
            "info",
        )
    )

    eq(
        response.success,
        True,
        "configured tokenizer service responds",
    )

    eq(
        response.data[
            "info"
        ][
            "ready"
        ],
        True,
        "configured tokenizer service starts ready",
    )

    encoded = service.handle(
        ServiceRequest(
            "tok-encode",
            "tokenizer_service",
            "encode",
            payload={
                "text": (
                    "software engineering"
                ),
                "add_bos": True,
                "add_eos": True,
            },
        )
    )

    eq(
        encoded.success,
        True,
        "configured tokenizer service encodes",
    )

    check(
        encoded.data[
            "token_count"
        ] > 0,
        "configured tokenizer service returns token IDs",
    )


def test_state_checksum_boundary():
    manager = (
        TokenizerConfigFactory()
        .initialize(
            training_config(),
            corpus=corpus(),
        )[
            "manager"
        ]
    )

    artifact = manager.save_state_file(
        ARTIFACT_PATH
    )

    original = open(
        ARTIFACT_PATH,
        "rb",
    ).read()

    corrupted = bytearray(
        original
    )

    corrupted[
        len(
            corrupted
        )
        - 1
    ] ^= 1

    open(
        ARTIFACT_PATH,
        "wb",
    ).write(
        bytes(
            corrupted
        )
    )

    expect_error(
        ValueError,
        lambda: (
            TokenizerConfigFactory()
            .initialize(
                TokenizerConfig(
                    mode="load",
                    artifact_path=(
                        ARTIFACT_PATH
                    ),
                )
            )
        ),
        "corrupted tokenizer artifact rejected by checksum",
    )

    check(
        artifact[
            "checksum"
        ] > 0,
        "tokenizer artifact exposes deterministic checksum",
    )


def main():
    cleanup()

    try:
        test_training_config()
        test_custom_special_validation()
        test_codec()
        test_train_and_persist()
        test_round_trip_load()
        test_deterministic_training()
        test_special_token_encoding()
        test_none_mode()
        test_train_requires_corpus()
        test_service_creation()
        test_state_checksum_boundary()

    finally:
        cleanup()

    print(
        "TOKENIZER CONFIG TEST SUITE: PASS"
    )
    print(
        "Assertions passed:",
        ASSERTIONS,
    )
    print(
        "Files validated: 5/5"
    )
    print(
        "Typed BPE training/bootstrap configuration: VALIDATED"
    )
    print(
        "Handwritten JSON decoding: VALIDATED"
    )
    print(
        "Real byte-level BPE training: VALIDATED"
    )
    print(
        "Deterministic tokenizer state: VALIDATED"
    )
    print(
        "Binary artifact persistence/checksum: VALIDATED"
    )
    print(
        "Exact artifact reload round trip: VALIDATED"
    )
    print(
        "Special-token encode/decode: VALIDATED"
    )
    print(
        "TokenizerService generation: VALIDATED"
    )
    print(
        "Third-party dependencies: 0"
    )


main()
