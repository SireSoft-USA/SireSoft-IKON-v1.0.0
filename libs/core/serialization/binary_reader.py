class BinaryReader:
    """
    Dependency-free counterpart to BinaryWriter.
    """

    def __init__(self, data):
        if isinstance(data, bytes):
            self._data = data
        elif isinstance(data, bytearray):
            self._data = bytes(data)
        else:
            raise TypeError("data must be bytes or bytearray")
        self._offset = 0

    def __len__(self):
        return len(self._data)

    def tell(self):
        return self._offset

    def remaining(self):
        return len(self._data) - self._offset

    def eof(self):
        return self._offset >= len(self._data)

    def seek(self, offset):
        if not isinstance(offset, int):
            raise TypeError("offset must be int")
        if offset < 0 or offset > len(self._data):
            raise IndexError("seek offset out of bounds")
        self._offset = offset

    def skip(self, count):
        if not isinstance(count, int):
            raise TypeError("count must be int")
        self.seek(self._offset + count)

    def _require(self, count):
        if count < 0:
            raise ValueError("count must be >= 0")
        if self._offset + count > len(self._data):
            raise EOFError("unexpected end of binary data")

    def _read_unsigned(self, byte_count):
        if byte_count <= 0:
            raise ValueError("byte_count must be > 0")
        self._require(byte_count)

        value = 0
        i = 0
        while i < byte_count:
            value |= self._data[self._offset + i] << (8 * i)
            i += 1

        self._offset += byte_count
        return value

    def _read_signed(self, byte_count):
        value = self._read_unsigned(byte_count)
        bits = byte_count * 8
        sign_bit = 1 << (bits - 1)
        if value & sign_bit:
            value -= 1 << bits
        return value

    def read_u8(self):
        return self._read_unsigned(1)

    def read_u16(self):
        return self._read_unsigned(2)

    def read_u32(self):
        return self._read_unsigned(4)

    def read_u64(self):
        return self._read_unsigned(8)

    def read_i8(self):
        return self._read_signed(1)

    def read_i16(self):
        return self._read_signed(2)

    def read_i32(self):
        return self._read_signed(4)

    def read_i64(self):
        return self._read_signed(8)

    def read_bool(self):
        value = self.read_u8()
        if value == 0:
            return False
        if value == 1:
            return True
        raise ValueError("invalid boolean encoding")

    def read_bytes(self, count):
        if not isinstance(count, int):
            raise TypeError("count must be int")
        self._require(count)

        start = self._offset
        end = start + count
        self._offset = end
        return self._data[start:end]

    def read_length_prefixed_bytes(self):
        length = self.read_varuint()
        return self.read_bytes(length)

    def read_varuint(self, max_bytes=10):
        if max_bytes <= 0:
            raise ValueError("max_bytes must be > 0")

        result = 0
        shift = 0
        count = 0

        while True:
            if count >= max_bytes:
                raise ValueError("varuint exceeds maximum encoded length")

            byte = self.read_u8()
            result |= (byte & 0x7F) << shift
            count += 1

            if (byte & 0x80) == 0:
                return result

            shift += 7

    def read_varint(self):
        encoded = self.read_varuint()
        if encoded & 1:
            return -((encoded >> 1) + 1)
        return encoded >> 1

    def read_f64(self):
        bits = self.read_u64()

        sign = -1.0 if ((bits >> 63) & 1) else 1.0
        exponent_bits = (bits >> 52) & 0x7FF
        mantissa = bits & ((1 << 52) - 1)

        if exponent_bits == 0x7FF:
            if mantissa == 0:
                return sign * float("inf")
            return float("nan")

        if exponent_bits == 0:
            if mantissa == 0:
                return -0.0 if sign < 0 else 0.0
            return sign * (mantissa / float(1 << 52)) * (2.0 ** -1022)

        exponent = exponent_bits - 1023
        significand = 1.0 + (mantissa / float(1 << 52))
        return sign * significand * (2.0 ** exponent)

    def read_text(self, codec=None):
        length = self.read_varuint()
        raw = self.read_bytes(length)

        if codec is None:
            return raw.decode("utf-8")
        return codec.decode(raw)
