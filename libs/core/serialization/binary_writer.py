class BinaryWriter:
    """
    Dependency-free binary writer used by SireLLM.

    Byte order is little-endian unless explicitly documented otherwise.
    The class deliberately uses only Python built-ins so model/checkpoint
    serialization does not depend on struct, pickle, NumPy, or third-party code.
    """

    def __init__(self, initial_capacity=0):
        if initial_capacity < 0:
            raise ValueError("initial_capacity must be >= 0")
        self._buffer = bytearray(initial_capacity)
        self._length = 0

    def __len__(self):
        return self._length

    def tell(self):
        return self._length

    def clear(self):
        self._buffer = bytearray()
        self._length = 0

    def _ensure(self, additional):
        if additional < 0:
            raise ValueError("additional must be >= 0")
        needed = self._length + additional
        current = len(self._buffer)
        if needed <= current:
            return

        capacity = 8 if current == 0 else current
        while capacity < needed:
            capacity *= 2

        new_buffer = bytearray(capacity)
        i = 0
        while i < self._length:
            new_buffer[i] = self._buffer[i]
            i += 1
        self._buffer = new_buffer

    def _write_unsigned(self, value, byte_count):
        if not isinstance(value, int):
            raise TypeError("value must be int")
        if byte_count <= 0:
            raise ValueError("byte_count must be > 0")

        max_value = (1 << (byte_count * 8)) - 1
        if value < 0 or value > max_value:
            raise OverflowError("unsigned integer out of range")

        self._ensure(byte_count)
        i = 0
        while i < byte_count:
            self._buffer[self._length + i] = (value >> (i * 8)) & 0xFF
            i += 1
        self._length += byte_count

    def _write_signed(self, value, byte_count):
        if not isinstance(value, int):
            raise TypeError("value must be int")
        bits = byte_count * 8
        minimum = -(1 << (bits - 1))
        maximum = (1 << (bits - 1)) - 1
        if value < minimum or value > maximum:
            raise OverflowError("signed integer out of range")

        if value < 0:
            value = (1 << bits) + value
        self._write_unsigned(value, byte_count)

    def write_u8(self, value):
        self._write_unsigned(value, 1)

    def write_u16(self, value):
        self._write_unsigned(value, 2)

    def write_u32(self, value):
        self._write_unsigned(value, 4)

    def write_u64(self, value):
        self._write_unsigned(value, 8)

    def write_i8(self, value):
        self._write_signed(value, 1)

    def write_i16(self, value):
        self._write_signed(value, 2)

    def write_i32(self, value):
        self._write_signed(value, 4)

    def write_i64(self, value):
        self._write_signed(value, 8)

    def write_bool(self, value):
        if value is True:
            self.write_u8(1)
        elif value is False:
            self.write_u8(0)
        else:
            raise TypeError("value must be bool")

    def write_bytes(self, data):
        if isinstance(data, bytearray):
            source = data
        elif isinstance(data, bytes):
            source = data
        else:
            raise TypeError("data must be bytes or bytearray")

        size = len(source)
        self._ensure(size)
        i = 0
        while i < size:
            self._buffer[self._length + i] = source[i]
            i += 1
        self._length += size

    def write_length_prefixed_bytes(self, data):
        self.write_varuint(len(data))
        self.write_bytes(data)

    def write_varuint(self, value):
        """
        Unsigned LEB128-style variable-length integer.
        """
        if not isinstance(value, int):
            raise TypeError("value must be int")
        if value < 0:
            raise ValueError("varuint cannot encode negative values")

        while True:
            byte = value & 0x7F
            value >>= 7
            if value:
                self.write_u8(byte | 0x80)
            else:
                self.write_u8(byte)
                break

    def write_varint(self, value):
        """
        Signed integer encoded with ZigZag + varuint.
        """
        if not isinstance(value, int):
            raise TypeError("value must be int")

        if value >= 0:
            zigzag = value << 1
        else:
            zigzag = ((-value) << 1) - 1
        self.write_varuint(zigzag)

    def write_f64(self, value):
        """
        Serialize a Python float as IEEE-754 binary64 without struct.
        """
        if not isinstance(value, (int, float)):
            raise TypeError("value must be numeric")
        value = float(value)

        if value != value:
            self.write_u64(0x7FF8000000000000)
            return

        if value == float("inf"):
            self.write_u64(0x7FF0000000000000)
            return

        if value == float("-inf"):
            self.write_u64(0xFFF0000000000000)
            return

        text = value.hex()
        sign = 0
        if text[0] == "-":
            sign = 1
            text = text[1:]

        if value == 0.0:
            bits = sign << 63
            self.write_u64(bits)
            return

        p_index = text.find("p")
        significand = text[2:p_index]
        exponent = int(text[p_index + 1:])

        dot_index = significand.find(".")
        lead = significand[:dot_index]
        fraction_hex = significand[dot_index + 1:]

        while len(fraction_hex) < 13:
            fraction_hex += "0"
        if len(fraction_hex) > 13:
            fraction_hex = fraction_hex[:13]

        fraction = int(fraction_hex, 16)

        if lead == "0":
            exponent_bits = 0
            mantissa_bits = fraction
        else:
            exponent_bits = exponent + 1023
            if exponent_bits <= 0 or exponent_bits >= 0x7FF:
                raise OverflowError("float exponent out of binary64 range")
            mantissa_bits = fraction & ((1 << 52) - 1)

        bits = (sign << 63) | (exponent_bits << 52) | mantissa_bits
        self.write_u64(bits)

    def write_text(self, text, codec=None):
        if not isinstance(text, str):
            raise TypeError("text must be str")

        if codec is None:
            encoded = text.encode("utf-8")
        else:
            encoded = codec.encode(text)

        self.write_varuint(len(encoded))
        self.write_bytes(encoded)

    def patch_u32(self, offset, value):
        if not isinstance(offset, int):
            raise TypeError("offset must be int")
        if offset < 0 or offset + 4 > self._length:
            raise IndexError("patch offset out of bounds")
        if value < 0 or value > 0xFFFFFFFF:
            raise OverflowError("u32 out of range")

        i = 0
        while i < 4:
            self._buffer[offset + i] = (value >> (8 * i)) & 0xFF
            i += 1

    def to_bytearray(self):
        output = bytearray(self._length)
        i = 0
        while i < self._length:
            output[i] = self._buffer[i]
            i += 1
        return output

    def to_bytes(self):
        return bytes(self.to_bytearray())
