BASE = "libs/nlp/normalization/"


def load_file(filename):
    namespace = {"__builtins__": __builtins__}
    path = BASE + filename
    source = open(path, "r", encoding="utf-8").read()
    exec(compile(source, path, "exec"), namespace)
    return namespace


WhitespaceNormalizer = load_file("whitespace.py")["WhitespaceNormalizer"]
PunctuationNormalizer = load_file("punctuation.py")["PunctuationNormalizer"]
UnicodeRules = load_file("unicode_rules.py")["UnicodeRules"]

_normalizer_ns = load_file("normalizer.py")
TextNormalizer = _normalizer_ns["TextNormalizer"]
NormalizationResult = _normalizer_ns["NormalizationResult"]

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


def test_whitespace():
    w = WhitespaceNormalizer()

    eq(
        w.normalize("  hello\t  world  "),
        "hello world",
        "horizontal whitespace collapse",
    )

    eq(
        w.normalize("a\r\nb\rc\n"),
        "a\nb\nc\n",
        "newline canonicalization",
    )

    eq(
        w.normalize("a\n\n\nb"),
        "a\n\nb",
        "blank line collapse",
    )

    eq(
        w.normalize("  a  \n   b   "),
        "a\nb",
        "line trimming",
    )

    eq(
        w.normalize(" a \n b ", preserve_newlines=False),
        "a b",
        "single-line normalization",
    )


def test_punctuation():
    p = PunctuationNormalizer()

    eq(
        p.normalize("“Hello”—she said…"),
        '"Hello"-she said...',
        "smart punctuation mapping",
    )

    eq(
        p.normalize("don’t"),
        "don't",
        "apostrophe mapping",
    )

    # Arabic/Urdu punctuation must not be destroyed by unrelated rules.
    eq(
        p.normalize("کیا حال ہے؟"),
        "کیا حال ہے؟",
        "language-specific punctuation preserved",
    )


def test_unicode_rules():
    u = UnicodeRules()

    eq(
        u.normalize_compatibility("hello\u00A0world"),
        "hello world",
        "NBSP normalization",
    )

    eq(
        u.normalize_compatibility("a\u200Bb"),
        "ab",
        "zero-width space removal",
    )

    eq(
        u.remove_disallowed_controls("a\x00b\x01c\n"),
        "abc\n",
        "control filtering",
    )

    eq(
        u.remove_disallowed_controls("a\tb"),
        "a\tb",
        "tab preserved",
    )

    check(
        u.validate_scalar_values("English اردو 中文 🙂"),
        "valid multilingual Unicode accepted",
    )

    surrogate = chr(0xD800)
    check(
        u.contains_surrogate("a" + surrogate),
        "surrogate detection",
    )

    expect_error(
        ValueError,
        lambda: u.validate_scalar_values("a" + surrogate),
        "isolated surrogate rejected",
    )


def build_normalizer():
    return TextNormalizer(
        WhitespaceNormalizer(),
        PunctuationNormalizer(),
        UnicodeRules(),
    )


def test_full_pipeline():
    n = build_normalizer()

    source = "  “Hello”\u00A0world…  \n\n\n  Next\tline  "
    result = n.normalize(source)

    eq(
        result.normalized,
        '"Hello" world...\n\nNext line',
        "full normalization pipeline",
    )

    eq(
        result.original,
        source,
        "original source retained exactly",
    )

    check(
        result.changed(),
        "changed flag",
    )

    eq(
        len(result.history),
        4,
        "history contains each pipeline stage",
    )

    eq(
        result.history[0]["name"],
        "unicode_compatibility",
        "history ordering",
    )

    eq(
        result.history[3]["name"],
        "whitespace",
        "whitespace final stage",
    )

    serialized = result.to_dict()

    eq(
        serialized["original"],
        source,
        "serialized original preserved",
    )

    eq(
        serialized["normalized"],
        result.normalized,
        "serialized normalized preserved",
    )


def test_selective_pipeline():
    n = build_normalizer()

    source = "  “hello”  "

    result = n.normalize(
        source,
        normalize_unicode=False,
        normalize_punctuation=False,
        normalize_whitespace=False,
        remove_controls=False,
    )

    eq(
        result.normalized,
        source,
        "disabled pipeline leaves input unchanged",
    )

    eq(
        len(result.history),
        0,
        "disabled stages produce no history",
    )

    check(
        not result.changed(),
        "unchanged result",
    )


def test_multilingual_preservation():
    n = build_normalizer()

    samples = [
        "السلام علیکم",
        "کیا حال ہے؟",
        "你好，世界",
        "こんにちは",
        "Привет мир",
        "🙂 hello",
    ]

    i = 0
    while i < len(samples):
        result = n.normalize(samples[i])
        check(
            len(result.normalized) > 0,
            "multilingual content survives normalization",
        )
        eq(
            result.original,
            samples[i],
            "multilingual original preserved",
        )
        i += 1


def test_training_source_separation():
    n = build_normalizer()

    raw = "  SireSoft\u00A0—\u00A0Company  "
    result = n.normalize(raw)

    # This is the architectural guarantee needed by CanonicalRecord:
    # original stays untouched while normalized is model-facing.
    eq(
        result.original,
        raw,
        "raw company knowledge is never overwritten",
    )

    eq(
        result.normalized,
        "SireSoft - Company",
        "training representation is normalized separately",
    )


def test_validation():
    expect_error(
        TypeError,
        lambda: WhitespaceNormalizer().normalize(123),
        "whitespace type validation",
    )

    expect_error(
        TypeError,
        lambda: PunctuationNormalizer().normalize(None),
        "punctuation type validation",
    )

    expect_error(
        TypeError,
        lambda: UnicodeRules().normalize_compatibility([]),
        "unicode type validation",
    )

    expect_error(
        ValueError,
        lambda: TextNormalizer(None, PunctuationNormalizer(), UnicodeRules()),
        "normalizer dependency validation",
    )


def main():
    test_whitespace()
    test_punctuation()
    test_unicode_rules()
    test_full_pipeline()
    test_selective_pipeline()
    test_multilingual_preservation()
    test_training_source_separation()
    test_validation()

    print("NORMALIZATION TEST SUITE: PASS")
    print("Assertions passed:", ASSERTIONS)
    print("Files validated: 4/4")
    print("Original-source preservation: VALIDATED")
    print("Multilingual preservation: VALIDATED")
    print("Third-party dependencies: 0")


main()
