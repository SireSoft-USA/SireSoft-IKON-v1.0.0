BASE = "libs/nlp/tokenizer/"


def load_file(filename):
    namespace = {"__builtins__": __builtins__}
    path = BASE + filename
    source = open(path, "r", encoding="utf-8").read()
    exec(compile(source, path, "exec"), namespace)
    return namespace


SpecialTokens = load_file("special_tokens.py")["SpecialTokens"]
ByteEncoder = load_file("byte_encoder.py")["ByteEncoder"]
PairCounter = load_file("pair_counter.py")["PairCounter"]
Vocabulary = load_file("vocabulary.py")["Vocabulary"]

_trainer_ns = load_file("bpe_trainer.py")
BPETrainer = _trainer_ns["BPETrainer"]
BPEModel = _trainer_ns["BPEModel"]

BPETokenizer = load_file("bpe_tokenizer.py")["BPETokenizer"]
TokenDecoder = load_file("decoder.py")["TokenDecoder"]

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


def build_model():
    byte_encoder = ByteEncoder()
    specials = SpecialTokens()
    trainer = BPETrainer(
        byte_encoder=byte_encoder,
        pair_counter=PairCounter(),
        vocabulary_factory=Vocabulary,
        special_tokens=specials,
    )

    corpus = [
        "hello hello hello",
        "hello world",
        "world world",
        "SireSoft builds software",
        "assistant user assistant",
        "Tell me a joke",
        "Why did the byte cross the bus?",
    ]

    model = trainer.train(
        corpus,
        vocab_size=320,
        min_frequency=2,
    )

    return model, byte_encoder, specials


def test_byte_encoder():
    encoder = ByteEncoder()

    samples = [
        "",
        "hello",
        "café",
        "اردو",
        "中文",
        "🙂",
        "mix اردو English 🙂",
    ]

    for sample in samples:
        encoded = encoder.encode_text(sample)
        decoded = encoder.decode_bytes(encoded)

        eq(
            decoded,
            sample,
            "byte encoder round trip",
        )

        eq(
            bytes(encoded),
            sample.encode("utf-8"),
            "manual UTF-8 matches standard bytes",
        )

    expect_error(
        ValueError,
        lambda: encoder.decode_bytes([0xC0, 0x80]),
        "invalid UTF-8 rejected",
    )


def test_special_tokens():
    specials = SpecialTokens()

    eq(
        specials.count(),
        9,
        "default special token count",
    )

    check(
        specials.contains("<USER>"),
        "USER token exists",
    )

    expect_error(
        ValueError,
        lambda: SpecialTokens(["<X>", "<X>"]),
        "duplicates rejected",
    )


def test_pair_counter():
    counter = PairCounter()

    counts = counter.count_sequences([
        [1, 2, 1, 2],
        [1, 2],
    ])

    eq(
        counts[(1, 2)],
        3,
        "pair frequency",
    )

    pair, frequency = counter.best_pair(
        counts,
        min_frequency=2,
    )

    eq(pair, (1, 2), "best pair")
    eq(frequency, 3, "best pair frequency")


def test_vocabulary():
    vocab = Vocabulary()

    eq(
        vocab.normal_token_count(),
        256,
        "base byte vocabulary",
    )

    merged = vocab.add_merge_token(
        ord("h"),
        ord("i"),
    )

    eq(
        vocab.token_bytes(merged),
        (ord("h"), ord("i")),
        "merge token bytes",
    )

    specials = SpecialTokens()
    vocab.finalize_special_tokens(
        specials.all()
    )

    check(
        vocab.is_special(
            vocab.special_id("<BOS>")
        ),
        "special ID registration",
    )

    expect_error(
        RuntimeError,
        lambda: vocab.add_merge_token(
            ord("a"),
            ord("b"),
        ),
        "merge after finalization rejected",
    )


def test_training():
    model, encoder, specials = build_model()

    check(
        len(model.merges) > 0,
        "BPE learned at least one merge",
    )

    check(
        model.vocabulary.size() <= 320,
        "trained vocabulary respects target",
    )

    state = model.export_state()

    check(
        "vocabulary" in state,
        "model state has vocabulary",
    )

    check(
        "merges" in state,
        "model state has merges",
    )


def test_tokenizer_round_trip():
    model, encoder, specials = build_model()

    tokenizer = BPETokenizer(
        model,
        encoder,
        specials,
    )

    samples = [
        "hello world",
        "SireSoft",
        "اردو text",
        "中文 example",
        "🙂 hello",
        "punctuation!?",
        "",
    ]

    for sample in samples:
        token_ids = tokenizer.encode(sample)
        restored = tokenizer.decode(token_ids)

        eq(
            restored,
            sample,
            "BPE round trip",
        )


def test_bpe_compression():
    model, encoder, specials = build_model()

    tokenizer = BPETokenizer(
        model,
        encoder,
        specials,
    )

    raw_bytes = encoder.encode_text(
        "hello hello hello"
    )

    tokens = tokenizer.encode(
        "hello hello hello"
    )

    check(
        len(tokens) < len(raw_bytes),
        "BPE reduces token count on learned text",
    )


def test_special_token_encoding():
    model, encoder, specials = build_model()

    tokenizer = BPETokenizer(
        model,
        encoder,
        specials,
    )

    ids = tokenizer.encode(
        "<USER>Hello<ASSISTANT>Hi",
        allow_special=True,
    )

    user_id = model.vocabulary.special_id(
        "<USER>"
    )

    assistant_id = model.vocabulary.special_id(
        "<ASSISTANT>"
    )

    check(
        user_id in ids,
        "USER special encoded as one ID",
    )

    check(
        assistant_id in ids,
        "ASSISTANT special encoded as one ID",
    )

    eq(
        tokenizer.decode(ids),
        "<USER>Hello<ASSISTANT>Hi",
        "special token round trip",
    )

    eq(
        tokenizer.decode(ids, skip_special=True),
        "HelloHi",
        "skip special tokens",
    )


def test_bos_eos():
    model, encoder, specials = build_model()

    tokenizer = BPETokenizer(
        model,
        encoder,
        specials,
    )

    ids = tokenizer.encode(
        "hello",
        add_bos=True,
        add_eos=True,
    )

    eq(
        ids[0],
        model.vocabulary.special_id("<BOS>"),
        "BOS first",
    )

    eq(
        ids[-1],
        model.vocabulary.special_id("<EOS>"),
        "EOS last",
    )


def test_decoder_facade():
    model, encoder, specials = build_model()

    tokenizer = BPETokenizer(
        model,
        encoder,
        specials,
    )

    decoder = TokenDecoder(tokenizer)

    ids = tokenizer.encode(
        "hello world"
    )

    eq(
        decoder.decode(ids),
        "hello world",
        "decode facade",
    )


def test_determinism():
    byte_encoder = ByteEncoder()
    specials = SpecialTokens()

    trainer = BPETrainer(
        byte_encoder,
        PairCounter(),
        Vocabulary,
        specials,
    )

    corpus = [
        "abab abab",
        "abab",
        "baba",
    ]

    first = trainer.train(
        corpus,
        vocab_size=280,
        min_frequency=2,
    )

    second = trainer.train(
        corpus,
        vocab_size=280,
        min_frequency=2,
    )

    eq(
        first.merges,
        second.merges,
        "training deterministic",
    )


def main():
    test_byte_encoder()
    test_special_tokens()
    test_pair_counter()
    test_vocabulary()
    test_training()
    test_tokenizer_round_trip()
    test_bpe_compression()
    test_special_token_encoding()
    test_bos_eos()
    test_decoder_facade()
    test_determinism()

    print("TOKENIZER TEST SUITE: PASS")
    print("Assertions passed:", ASSERTIONS)
    print("Files validated: 7/7")
    print("Byte-level UTF-8 encoding: VALIDATED")
    print("Deterministic BPE training: VALIDATED")
    print("Multilingual round trip: VALIDATED")
    print("Special-token handling: VALIDATED")
    print("Third-party dependencies: 0")


main()
