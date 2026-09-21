import os

SERIAL_BASE = "libs/core/serialization/"
TOKENIZER_BASE = "libs/nlp/tokenizer/"
PROTOCOL_BASE = "libs/protocol/"
SERVICE_BASE = "services/tokenizer_service/"

namespace = {
    "__builtins__": __builtins__,
}

for filename in [
    "binary_writer.py",
    "binary_reader.py",
    "checksum.py",
]:
    path = SERIAL_BASE + filename

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
    "special_tokens.py",
    "byte_encoder.py",
    "pair_counter.py",
    "vocabulary.py",
    "bpe_trainer.py",
    "bpe_tokenizer.py",
]:
    path = TOKENIZER_BASE + filename

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
    "error.py",
    "message.py",
    "request.py",
    "response.py",
    "validator.py",
    "codec.py",
]:
    path = PROTOCOL_BASE + filename

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
    "artifact.py",
    "state_codec.py",
    "manager.py",
    "service.py",
]:
    path = SERVICE_BASE + filename

    source = open(
        path,
        "r",
        encoding="utf-8",
    ).read()

    if "import " in source:
        raise AssertionError(
            "tokenizer_service implementation contains forbidden import: "
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
STATE_PATH = (
    "services/tokenizer_service/"
    "_test_tokenizer.sltok"
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
        + repr(expected)
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


def corpus():
    return [
        "hello hello hello",
        "hello world world",
        "SireSoft builds software systems",
        "software engineering services",
        "artificial intelligence systems",
        "assistant user assistant",
        "اردو software",
        "中文 software",
    ]


def trained_manager():
    manager = (
        build_tokenizer_manager()
    )

    manager.train(
        corpus(),
        vocab_size=320,
        min_frequency=2,
    )

    return manager


def test_initial_state():
    manager = (
        build_tokenizer_manager()
    )

    eq(
        manager.ready(),
        False,
        "new manager not ready",
    )

    eq(
        manager.info()[
            "vocabulary_size"
        ],
        0,
        "new manager vocab size",
    )

    expect_error(
        RuntimeError,
        lambda: manager.encode(
            "hello"
        ),
        "encode before load rejected",
    )


def test_training():
    manager = trained_manager()

    info = manager.info()

    eq(
        info["ready"],
        True,
        "manager ready after training",
    )

    check(
        info["merge_count"] > 0,
        "training learns merges",
    )

    check(
        info[
            "vocabulary_size"
        ] <= 320,
        "vocabulary respects configured target",
    )

    eq(
        info[
            "special_token_count"
        ],
        9,
        "default special token count",
    )


def test_round_trip_multilingual():
    manager = trained_manager()

    samples = [
        "hello world",
        "SireSoft software",
        "اردو text",
        "中文 example",
        "🙂 hello",
        "",
    ]

    for sample in samples:
        token_ids = manager.encode(
            sample
        )

        restored = manager.decode(
            token_ids
        )

        eq(
            restored,
            sample,
            "multilingual encode/decode round trip",
        )


def test_special_flags():
    manager = trained_manager()

    ids = manager.encode(
        "<USER>Hello<ASSISTANT>Hi",
        add_bos=True,
        add_eos=True,
        allow_special=True,
    )

    vocab = manager.model.vocabulary

    eq(
        ids[0],
        vocab.special_id(
            "<BOS>"
        ),
        "BOS added",
    )

    eq(
        ids[-1],
        vocab.special_id(
            "<EOS>"
        ),
        "EOS added",
    )

    check(
        vocab.special_id(
            "<USER>"
        )
        in ids,
        "USER special recognized",
    )

    decoded = manager.decode(
        ids,
        skip_special=False,
    )

    eq(
        decoded,
        (
            "<BOS><USER>Hello"
            "<ASSISTANT>Hi<EOS>"
        ),
        "specials preserved in decode",
    )

    plain = manager.decode(
        ids,
        skip_special=True,
    )

    eq(
        plain,
        "HelloHi",
        "specials skipped in decode",
    )


def test_deterministic_training():
    first = trained_manager()
    second = trained_manager()

    eq(
        first.export_state(),
        second.export_state(),
        "same corpus/config gives deterministic tokenizer state",
    )

    eq(
        first.encode(
            "SireSoft software"
        ),
        second.encode(
            "SireSoft software"
        ),
        "deterministic token IDs",
    )


def test_state_dict_round_trip():
    original = trained_manager()

    state = original.export_state()

    restored = (
        build_tokenizer_manager()
    )

    restored.load_state(
        state
    )

    eq(
        restored.export_state(),
        state,
        "tokenizer state dict exact round trip",
    )

    samples = [
        "hello world",
        "SireSoft builds software",
        "اردو software",
    ]

    for sample in samples:
        eq(
            restored.encode(
                sample
            ),
            original.encode(
                sample
            ),
            "restored tokenizer preserves IDs",
        )


def test_protocol_safe_state():
    manager = trained_manager()
    state = manager.export_state()

    codec = ProtocolCodec()

    request = ServiceRequest(
        "artifact",
        "tokenizer_service",
        "load_state",
        payload={
            "state": state,
        },
    )

    restored_request = (
        codec.decode_request(
            codec.encode_request(
                request
            )
        )
    )

    eq(
        restored_request.payload[
            "state"
        ],
        state,
        "tokenizer artifact survives protocol codec",
    )


def test_binary_state_file():
    if os.path.exists(
        STATE_PATH
    ):
        os.remove(
            STATE_PATH
        )

    manager = trained_manager()

    result = manager.save_state_file(
        STATE_PATH
    )

    check(
        result["bytes"] > 0,
        "binary tokenizer artifact written",
    )

    check(
        os.path.isfile(
            STATE_PATH
        ),
        "tokenizer artifact file exists",
    )

    restored = (
        build_tokenizer_manager()
    )

    restored.load_state_file(
        STATE_PATH
    )

    eq(
        restored.export_state(),
        manager.export_state(),
        "binary tokenizer artifact exact round trip",
    )

    eq(
        restored.encode(
            "hello software"
        ),
        manager.encode(
            "hello software"
        ),
        "binary restored tokenizer preserves IDs",
    )


def test_state_corruption_detection():
    manager = trained_manager()
    encoded = bytearray(
        manager.state_codec.encode(
            manager.artifact
        )
    )

    encoded[-1] ^= 0x01

    expect_error(
        ValueError,
        lambda: manager.state_codec.decode(
            bytes(
                encoded
            )
        ),
        "artifact checksum detects corruption",
    )


def test_vocabulary_inspection():
    manager = trained_manager()

    byte_entry = (
        manager
        .vocabulary_entry(
            ord(
                "A"
            )
        )
    )

    eq(
        byte_entry["kind"],
        "byte",
        "base token identified as byte",
    )

    eq(
        byte_entry["bytes"],
        [
            ord(
                "A"
            )
        ],
        "base token bytes",
    )

    special_id = (
        manager
        .model
        .vocabulary
        .special_id(
            "<BOS>"
        )
    )

    special_entry = (
        manager
        .vocabulary_entry(
            special_id
        )
    )

    eq(
        special_entry[
            "kind"
        ],
        "special",
        "special vocab inspection",
    )

    eq(
        special_entry[
            "token"
        ],
        "<BOS>",
        "special token text",
    )


def test_service_train_encode_decode():
    service = TokenizerService(
        build_tokenizer_manager()
    )

    trained = service.handle(
        ServiceRequest(
            "r1",
            "tokenizer_service",
            "train",
            payload={
                "corpus": corpus(),
                "vocab_size": 320,
                "min_frequency": 2,
            },
        )
    )

    eq(
        trained.success,
        True,
        "service training succeeds",
    )

    encoded = service.handle(
        ServiceRequest(
            "r2",
            "tokenizer_service",
            "encode",
            payload={
                "text": "hello world",
                "add_bos": True,
                "add_eos": True,
            },
        )
    )

    eq(
        encoded.success,
        True,
        "service encode succeeds",
    )

    check(
        encoded.data[
            "token_count"
        ] > 2,
        "service encoded token count",
    )

    decoded = service.handle(
        ServiceRequest(
            "r3",
            "tokenizer_service",
            "decode",
            payload={
                "token_ids": (
                    encoded.data[
                        "token_ids"
                    ]
                ),
                "skip_special": True,
            },
        )
    )

    eq(
        decoded.data[
            "text"
        ],
        "hello world",
        "service decode",
    )


def test_service_state_transfer():
    source_service = TokenizerService(
        trained_manager()
    )

    exported = source_service.handle(
        ServiceRequest(
            "e1",
            "tokenizer_service",
            "export_state",
        )
    )

    target_service = TokenizerService(
        build_tokenizer_manager()
    )

    loaded = target_service.handle(
        ServiceRequest(
            "e2",
            "tokenizer_service",
            "load_state",
            payload={
                "state": exported.data[
                    "state"
                ],
            },
        )
    )

    eq(
        loaded.success,
        True,
        "service state load succeeds",
    )

    first = source_service.handle(
        ServiceRequest(
            "e3",
            "tokenizer_service",
            "encode",
            payload={
                "text": "SireSoft software",
            },
        )
    )

    second = target_service.handle(
        ServiceRequest(
            "e4",
            "tokenizer_service",
            "encode",
            payload={
                "text": "SireSoft software",
            },
        )
    )

    eq(
        first.data[
            "token_ids"
        ],
        second.data[
            "token_ids"
        ],
        "state transfer preserves token IDs",
    )


def test_service_protocol_round_trip():
    service = TokenizerService(
        build_tokenizer_manager()
    )

    codec = ProtocolCodec()

    train_request = ServiceRequest(
        "protocol-train",
        "tokenizer_service",
        "train",
        payload={
            "corpus": corpus(),
            "vocab_size": 320,
            "min_frequency": 2,
        },
        trace_id="trace-tokenizer",
    )

    restored_request = (
        codec.decode_request(
            codec.encode_request(
                train_request
            )
        )
    )

    response = service.handle(
        restored_request
    )

    restored_response = (
        codec.decode_response(
            codec.encode_response(
                response
            )
        )
    )

    eq(
        restored_response.success,
        True,
        "tokenizer service works through protocol codec",
    )

    eq(
        restored_response.trace_id,
        "trace-tokenizer",
        "tokenizer trace ID preserved",
    )

    check(
        restored_response.data[
            "info"
        ]["merge_count"] > 0,
        "protocol response contains trained tokenizer info",
    )


def test_service_not_ready_error():
    service = TokenizerService(
        build_tokenizer_manager()
    )

    response = service.handle(
        ServiceRequest(
            "x",
            "tokenizer_service",
            "encode",
            payload={
                "text": "hello",
            },
        )
    )

    eq(
        response.success,
        False,
        "unready service encode fails",
    )

    eq(
        response.error.code,
        "MODEL_NOT_READY",
        "unready tokenizer error code",
    )

    eq(
        response.error.retryable,
        True,
        "unready tokenizer error retryable",
    )


def test_service_info_and_vocab():
    service = TokenizerService(
        trained_manager()
    )

    info = service.handle(
        ServiceRequest(
            "i1",
            "tokenizer_service",
            "info",
        )
    )

    eq(
        info.data[
            "info"
        ]["ready"],
        True,
        "service info ready",
    )

    entry = service.handle(
        ServiceRequest(
            "i2",
            "tokenizer_service",
            "vocabulary_entry",
            payload={
                "token_id": ord(
                    "S"
                ),
            },
        )
    )

    eq(
        entry.data[
            "entry"
        ]["kind"],
        "byte",
        "service vocabulary inspection",
    )


def test_validation():
    manager = (
        build_tokenizer_manager()
    )

    expect_error(
        ValueError,
        lambda: manager.train(
            [],
        ),
        "empty tokenizer corpus rejected",
    )

    expect_error(
        ValueError,
        lambda: TokenizerArtifact.from_dict({
            "version": 999,
            "special_tokens": [],
            "merges": [],
            "target_vocab_size": 300,
            "min_frequency": 2,
        }),
        "unsupported artifact version rejected",
    )

    service = TokenizerService(
        manager
    )

    wrong = service.handle(
        ServiceRequest(
            "w",
            "rag_service",
            "info",
        )
    )

    eq(
        wrong.error.code,
        "INVALID_REQUEST",
        "wrong target service rejected",
    )

    unsupported = service.handle(
        ServiceRequest(
            "u",
            "tokenizer_service",
            "unknown",
        )
    )

    eq(
        unsupported.error.code,
        "INVALID_REQUEST",
        "unsupported operation rejected",
    )

    expect_error(
        TypeError,
        lambda: service.handle(
            {}
        ),
        "non-ServiceRequest rejected",
    )


def main():
    try:
        test_initial_state()
        test_training()
        test_round_trip_multilingual()
        test_special_flags()
        test_deterministic_training()
        test_state_dict_round_trip()
        test_protocol_safe_state()
        test_binary_state_file()
        test_state_corruption_detection()
        test_vocabulary_inspection()
        test_service_train_encode_decode()
        test_service_state_transfer()
        test_service_protocol_round_trip()
        test_service_not_ready_error()
        test_service_info_and_vocab()
        test_validation()

    finally:
        if os.path.exists(
            STATE_PATH
        ):
            os.remove(
                STATE_PATH
            )

    print(
        "TOKENIZER SERVICE TEST SUITE: PASS"
    )
    print(
        "Assertions passed:",
        ASSERTIONS,
    )
    print(
        "Files validated: 4/4"
    )
    print(
        "Byte-BPE training service: VALIDATED"
    )
    print(
        "Multilingual encode/decode: VALIDATED"
    )
    print(
        "BOS/EOS/special-token handling: VALIDATED"
    )
    print(
        "Deterministic tokenizer state: VALIDATED"
    )
    print(
        "Binary state persistence/checksum: VALIDATED"
    )
    print(
        "Protocol-safe state transfer: VALIDATED"
    )
    print(
        "Vocabulary inspection: VALIDATED"
    )
    print(
        "Protocol service operations: VALIDATED"
    )
    print(
        "Third-party dependencies: 0"
    )


main()
