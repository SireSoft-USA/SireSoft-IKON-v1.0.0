# SireLLM serialization validation suite.
# Intentionally uses no imports or external testing framework.

BASE = "libs/core/serialization/"

def load_file(filename):
    namespace = {"__builtins__": __builtins__}
    path = BASE + filename
    source = open(path, "r", encoding="utf-8").read()
    exec(compile(source, path, "exec"), namespace)
    return namespace


_writer_ns = load_file("binary_writer.py")
_reader_ns = load_file("binary_reader.py")
_codec_ns = load_file("text_codec.py")
_checksum_ns = load_file("checksum.py")

BinaryWriter = _writer_ns["BinaryWriter"]
BinaryReader = _reader_ns["BinaryReader"]
UTF8Codec = _codec_ns["UTF8Codec"]

fnv1a32 = _checksum_ns["fnv1a32"]
fnv1a64 = _checksum_ns["fnv1a64"]
adler32 = _checksum_ns["adler32"]
crc32 = _checksum_ns["crc32"]
checksum_hex = _checksum_ns["checksum_hex"]

ASSERTIONS = 0


def check(condition, message):
    global ASSERTIONS
    ASSERTIONS += 1
    if not condition:
        raise AssertionError(message)


def check_equal(actual, expected, message):
    check(actual == expected, message + " | got=" + repr(actual) + " expected=" + repr(expected))


def check_close(actual, expected, tolerance, message):
    delta = actual - expected
    if delta < 0:
        delta = -delta
    check(delta <= tolerance, message + " | got=" + repr(actual) + " expected=" + repr(expected))


def expect_error(error_type, fn, message):
    global ASSERTIONS
    ASSERTIONS += 1
    try:
        fn()
    except error_type:
        return
    except Exception as exc:
        raise AssertionError(message + " | wrong exception: " + repr(exc))
    raise AssertionError(message + " | expected exception was not raised")


def test_utf8():
    codec = UTF8Codec()

    samples = [
        "",
        "hello",
        "SireSoft",
        "café",
        "السلام علیکم",
        "你好",
        "emoji: 🙂",
        "𐍈",
    ]

    i = 0
    while i < len(samples):
        sample = samples[i]
        encoded = codec.encode(sample)
        decoded = codec.decode(encoded)
        check_equal(decoded, sample, "UTF-8 round trip")
        check_equal(encoded, sample.encode("utf-8"), "UTF-8 bytes match standard encoding")
        i += 1

    expect_error(
        UnicodeDecodeError,
        lambda: codec.decode(bytes([0xC0, 0x80])),
        "overlong UTF-8 must fail",
    )
    expect_error(
        UnicodeDecodeError,
        lambda: codec.decode(bytes([0xE2, 0x82])),
        "truncated UTF-8 must fail",
    )


def test_integer_round_trip():
    writer = BinaryWriter()

    writer.write_u8(255)
    writer.write_u16(65535)
    writer.write_u32(4294967295)
    writer.write_u64(18446744073709551615)

    writer.write_i8(-128)
    writer.write_i16(-32768)
    writer.write_i32(-2147483648)
    writer.write_i64(-9223372036854775808)

    writer.write_bool(True)
    writer.write_bool(False)

    reader = BinaryReader(writer.to_bytes())

    check_equal(reader.read_u8(), 255, "u8")
    check_equal(reader.read_u16(), 65535, "u16")
    check_equal(reader.read_u32(), 4294967295, "u32")
    check_equal(reader.read_u64(), 18446744073709551615, "u64")

    check_equal(reader.read_i8(), -128, "i8")
    check_equal(reader.read_i16(), -32768, "i16")
    check_equal(reader.read_i32(), -2147483648, "i32")
    check_equal(reader.read_i64(), -9223372036854775808, "i64")

    check_equal(reader.read_bool(), True, "bool true")
    check_equal(reader.read_bool(), False, "bool false")
    check(reader.eof(), "reader should be at EOF")


def test_varints():
    unsigned = [0, 1, 127, 128, 255, 16384, 999999999, 1 << 63]
    signed = [0, 1, -1, 63, -64, 1024, -1024, 999999999, -999999999]

    writer = BinaryWriter()

    i = 0
    while i < len(unsigned):
        writer.write_varuint(unsigned[i])
        i += 1

    i = 0
    while i < len(signed):
        writer.write_varint(signed[i])
        i += 1

    reader = BinaryReader(writer.to_bytes())

    i = 0
    while i < len(unsigned):
        check_equal(reader.read_varuint(), unsigned[i], "varuint round trip")
        i += 1

    i = 0
    while i < len(signed):
        check_equal(reader.read_varint(), signed[i], "varint round trip")
        i += 1


def test_float_round_trip():
    values = [
        0.0,
        -0.0,
        1.0,
        -1.0,
        3.141592653589793,
        1.0e-300,
        1.0e300,
        float("inf"),
        float("-inf"),
    ]

    writer = BinaryWriter()
    i = 0
    while i < len(values):
        writer.write_f64(values[i])
        i += 1

    reader = BinaryReader(writer.to_bytes())

    i = 0
    while i < len(values):
        actual = reader.read_f64()
        expected = values[i]

        if expected == float("inf") or expected == float("-inf"):
            check_equal(actual, expected, "infinity round trip")
        elif expected == 0.0:
            check_equal(actual, expected, "zero round trip")
        else:
            relative = abs((actual - expected) / expected)
            check(relative <= 1e-15, "float64 round trip")

        i += 1

    writer = BinaryWriter()
    writer.write_f64(float("nan"))
    result = BinaryReader(writer.to_bytes()).read_f64()
    check(result != result, "NaN must remain NaN")


def test_text_and_bytes():
    codec = UTF8Codec()
    writer = BinaryWriter()

    writer.write_text("SireLLM", codec)
    writer.write_text("from scratch — لاہور", codec)
    writer.write_length_prefixed_bytes(bytes([1, 2, 3, 4, 255]))

    reader = BinaryReader(writer.to_bytes())

    check_equal(reader.read_text(codec), "SireLLM", "ASCII text")
    check_equal(reader.read_text(codec), "from scratch — لاہور", "Unicode text")
    check_equal(
        reader.read_length_prefixed_bytes(),
        bytes([1, 2, 3, 4, 255]),
        "length-prefixed bytes",
    )


def test_patch_and_position():
    writer = BinaryWriter()
    writer.write_u32(0)
    payload_start = writer.tell()
    writer.write_bytes(b"abcdef")
    payload_size = writer.tell() - payload_start
    writer.patch_u32(0, payload_size)

    reader = BinaryReader(writer.to_bytes())
    check_equal(reader.read_u32(), 6, "patched payload length")
    check_equal(reader.tell(), 4, "tell after u32")
    check_equal(reader.read_bytes(6), b"abcdef", "patched payload content")

    reader.seek(4)
    reader.skip(2)
    check_equal(reader.tell(), 6, "seek/skip")


def test_checksums():
    # Published/common verification vectors.
    data = b"123456789"

    check_equal(crc32(data), 0xCBF43926, "CRC-32 known vector")
    check_equal(adler32(data), 0x091E01DE, "Adler-32 known vector")
    check_equal(fnv1a32(b""), 0x811C9DC5, "FNV-1a 32 empty vector")
    check_equal(fnv1a64(b""), 0xCBF29CE484222325, "FNV-1a 64 empty vector")
    check_equal(checksum_hex(0xABCD, 8), "0000abcd", "checksum hex formatting")


def test_bounds_and_errors():
    expect_error(OverflowError, lambda: BinaryWriter().write_u8(256), "u8 overflow")
    expect_error(OverflowError, lambda: BinaryWriter().write_i8(-129), "i8 overflow")
    expect_error(ValueError, lambda: BinaryWriter().write_varuint(-1), "negative varuint")
    expect_error(EOFError, lambda: BinaryReader(b"\x01").read_u16(), "reader EOF")
    expect_error(ValueError, lambda: BinaryReader(b"\x02").read_bool(), "invalid bool")


def main():
    test_utf8()
    test_integer_round_trip()
    test_varints()
    test_float_round_trip()
    test_text_and_bytes()
    test_patch_and_position()
    test_checksums()
    test_bounds_and_errors()

    print("SERIALIZATION TEST SUITE: PASS")
    print("Assertions passed:", ASSERTIONS)
    print("Files validated: 4/4")
    print("External dependencies: 0")


main()
