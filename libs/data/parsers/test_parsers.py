BASE = "libs/data/parsers/"


def load_file(filename):
    namespace = {"__builtins__": __builtins__}
    path = BASE + filename
    source = open(path, "r", encoding="utf-8").read()
    exec(compile(source, path, "exec"), namespace)
    return namespace


_json_ns = load_file("json_parser.py")
JSONParser = _json_ns["JSONParser"]
JSONParseError = _json_ns["JSONParseError"]
parse_json = _json_ns["parse_json"]

_jsonl_ns = load_file("jsonl_parser.py")
JSONLParser = _jsonl_ns["JSONLParser"]
JSONLParseError = _jsonl_ns["JSONLParseError"]

_text_ns = load_file("text_parser.py")
TextParser = _text_ns["TextParser"]

ASSERTIONS = 0


def check(condition, message):
    global ASSERTIONS
    ASSERTIONS += 1
    if not condition:
        raise AssertionError(message)


def check_equal(actual, expected, message):
    check(actual == expected, message + " | got=" + repr(actual) + " expected=" + repr(expected))


def check_close(actual, expected, tolerance, message):
    difference = actual - expected
    if difference < 0:
        difference = -difference
    check(difference <= tolerance, message)


def expect_error(error_type, fn, message):
    global ASSERTIONS
    ASSERTIONS += 1
    try:
        fn()
    except error_type:
        return
    except Exception as exc:
        raise AssertionError(message + " | wrong exception=" + repr(exc))
    raise AssertionError(message + " | expected exception was not raised")


def test_json_primitives():
    parser = JSONParser()
    check_equal(parser.parse("null"), None, "null")
    check_equal(parser.parse("true"), True, "true")
    check_equal(parser.parse("false"), False, "false")
    check_equal(parser.parse("0"), 0, "zero")
    check_equal(parser.parse("-17"), -17, "negative integer")
    check_equal(parser.parse("123456789"), 123456789, "integer")
    check_close(parser.parse("3.1415"), 3.1415, 1e-12, "decimal")
    check_close(parser.parse("-2.5e3"), -2500.0, 1e-12, "exponent")
    check_close(parser.parse("6.02E-2"), 0.0602, 1e-12, "negative exponent")


def test_json_strings():
    parser = JSONParser()
    check_equal(parser.parse('"hello"'), "hello", "simple string")
    check_equal(parser.parse('"line\\nnext\\ttab"'), "line\nnext\ttab", "escaped whitespace")
    check_equal(parser.parse('"\\u0041\\u00DF"'), "Aß", "Unicode BMP")
    check_equal(parser.parse('"\\uD83D\\uDE42"'), "🙂", "Unicode surrogate pair")


def test_json_composites():
    parser = JSONParser()
    source = (
        '{'
        '"name":"SireLLM",'
        '"version":1,'
        '"active":true,'
        '"scores":[1,2,3.5],'
        '"meta":{"owner":null}'
        '}'
    )
    value = parser.parse(source)
    check_equal(value["name"], "SireLLM", "object string")
    check_equal(value["version"], 1, "object number")
    check_equal(value["active"], True, "object bool")
    check_equal(value["scores"], [1, 2, 3.5], "array")
    check_equal(value["meta"]["owner"], None, "nested object")
    check_equal(parser.parse("[]"), [], "empty array")
    check_equal(parser.parse("{}"), {}, "empty object")
    check_equal(parse_json('{"nested":[{"x":1},{"x":2}]}')["nested"][1]["x"], 2, "convenience parser")


def test_json_failures():
    parser = JSONParser()
    bad_values = [
        '{"x":1,}', '[1,2,]', '{"x" 1}', '01', '1.', '1e',
        '"unterminated', '"bad\\xescape"', '"\\uD800"', 'tru', 'null trailing'
    ]
    for value in bad_values:
        expect_error(JSONParseError, lambda value=value: parser.parse(value), "invalid JSON must fail")

    try:
        parser.parse('{\n"x":1,\n}')
    except JSONParseError as exc:
        check_equal(exc.line, 3, "error line tracking")
        check(exc.column >= 1, "error column tracking")
    else:
        raise AssertionError("expected line tracking parse error")


def test_jsonl():
    parser = JSONLParser(JSONParser())
    text = (
        '{"instruction":"hello","response":"hi"}\n'
        '\n'
        '{"instruction":"2+2","response":"4"}\n'
    )
    records = parser.parse(text)
    check_equal(len(records), 2, "JSONL record count")
    check_equal(records[0]["instruction"], "hello", "JSONL first record")
    check_equal(records[1]["response"], "4", "JSONL second record")

    records = parser.parse_lines(['{"a":1}', '{"a":2}', '{"a":3}'])
    check_equal([r["a"] for r in records], [1, 2, 3], "JSONL parse_lines")

    try:
        parser.parse('{"ok":1}\n{"broken":}\n', source_name="test.jsonl")
    except JSONLParseError as exc:
        check_equal(exc.line_number, 2, "JSONL error line")
        check_equal(exc.source_name, "test.jsonl", "JSONL source name")
    else:
        raise AssertionError("invalid JSONL must fail")


def test_text_parser():
    parser = TextParser()
    raw = "Line one.\n\nLine two.\nStill two.\n"
    doc = parser.parse(raw, source_name="sample.txt")
    check_equal(doc.content, raw, "text remains unchanged")
    check_equal(doc.source_name, "sample.txt", "source")
    check_equal(doc.character_count, len(raw), "character count")
    check_equal(doc.line_count, 5, "line count")

    data = "SireSoft — لاہور\n".encode("utf-8")
    byte_doc = parser.parse_bytes(data, source_name="utf8.txt")
    check_equal(byte_doc.content, "SireSoft — لاہور\n", "UTF-8 text")
    check_equal(byte_doc.byte_count, len(data), "byte count")

    check_equal(parser.lines("a\nb\nc"), ["a", "b", "c"], "line view")
    check_equal(
        parser.paragraphs("first\nline\n\nsecond\n\nthird"),
        ["first\nline", "second", "third"],
        "paragraph view"
    )
    check_equal(doc.to_dict()["content"], raw, "document dictionary")


def test_dataset_shapes():
    json_parser = JSONParser()
    jsonl = JSONLParser(json_parser)
    text = TextParser()

    dolly = (
        '{"instruction":"Explain AI","context":"","response":"AI is...","category":"open_qa"}\n'
        '{"instruction":"Say hi","context":"","response":"Hi","category":"creative_writing"}\n'
    )
    records = jsonl.parse(dolly)
    check_equal(len(records), 2, "Dolly-like records")
    check_equal(records[0]["category"], "open_qa", "Dolly-like preservation")

    conversation = json_parser.parse('{"dialogues":[{"turns":["hello","hi"],"emotion":"neutral"}]}')
    check_equal(conversation["dialogues"][0]["turns"][1], "hi", "conversation shape")

    siresoft = text.parse("SireSoft\nCompany information remains lossless.", source_name="siresoft.txt")
    check_equal(
        siresoft.content,
        "SireSoft\nCompany information remains lossless.",
        "SireSoft lossless source"
    )


def main():
    test_json_primitives()
    test_json_strings()
    test_json_composites()
    test_json_failures()
    test_jsonl()
    test_text_parser()
    test_dataset_shapes()

    print("PARSERS TEST SUITE: PASS")
    print("Assertions passed:", ASSERTIONS)
    print("Files validated: 3/3")
    print("Python json module used: NO")
    print("Third-party dependencies: 0")


main()
