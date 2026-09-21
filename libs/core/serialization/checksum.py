def fnv1a32(data):
    if isinstance(data, str):
        data = data.encode("utf-8")
    if isinstance(data, bytearray):
        data = bytes(data)
    if not isinstance(data, bytes):
        raise TypeError("data must be bytes, bytearray, or str")

    value = 0x811C9DC5
    i = 0
    while i < len(data):
        value ^= data[i]
        value = (value * 0x01000193) & 0xFFFFFFFF
        i += 1
    return value


def fnv1a64(data):
    if isinstance(data, str):
        data = data.encode("utf-8")
    if isinstance(data, bytearray):
        data = bytes(data)
    if not isinstance(data, bytes):
        raise TypeError("data must be bytes, bytearray, or str")

    value = 0xCBF29CE484222325
    i = 0
    while i < len(data):
        value ^= data[i]
        value = (value * 0x100000001B3) & 0xFFFFFFFFFFFFFFFF
        i += 1
    return value


def adler32(data):
    if isinstance(data, str):
        data = data.encode("utf-8")
    if isinstance(data, bytearray):
        data = bytes(data)
    if not isinstance(data, bytes):
        raise TypeError("data must be bytes, bytearray, or str")

    modulus = 65521
    a = 1
    b = 0
    i = 0

    while i < len(data):
        a = (a + data[i]) % modulus
        b = (b + a) % modulus
        i += 1

    return ((b << 16) | a) & 0xFFFFFFFF


def crc32(data):
    """
    CRC-32/ISO-HDLC, polynomial 0xEDB88320.
    Table-free implementation to keep the primitive fully handwritten.
    """
    if isinstance(data, str):
        data = data.encode("utf-8")
    if isinstance(data, bytearray):
        data = bytes(data)
    if not isinstance(data, bytes):
        raise TypeError("data must be bytes, bytearray, or str")

    crc = 0xFFFFFFFF
    i = 0

    while i < len(data):
        crc ^= data[i]
        bit = 0

        while bit < 8:
            if crc & 1:
                crc = (crc >> 1) ^ 0xEDB88320
            else:
                crc >>= 1
            bit += 1

        i += 1

    return (crc ^ 0xFFFFFFFF) & 0xFFFFFFFF


def checksum_hex(value, width=8):
    if not isinstance(value, int):
        raise TypeError("value must be int")
    if width <= 0:
        raise ValueError("width must be > 0")

    text = hex(value)[2:]
    if len(text) < width:
        text = ("0" * (width - len(text))) + text
    return text[-width:]
