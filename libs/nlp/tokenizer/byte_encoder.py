class ByteEncoder:
    """
    UTF-8 byte encoder/decoder implemented without codecs/json/tokenizer libs.
    """

    def encode_text(self, text):
        if not isinstance(text, str):
            raise TypeError("text must be str")

        out = []
        i = 0

        while i < len(text):
            cp = ord(text[i])

            if 0xD800 <= cp <= 0xDFFF:
                raise ValueError("isolated Unicode surrogate at index " + str(i))

            if cp <= 0x7F:
                out.append(cp)

            elif cp <= 0x7FF:
                out.append(0xC0 | (cp >> 6))
                out.append(0x80 | (cp & 0x3F))

            elif cp <= 0xFFFF:
                out.append(0xE0 | (cp >> 12))
                out.append(0x80 | ((cp >> 6) & 0x3F))
                out.append(0x80 | (cp & 0x3F))

            elif cp <= 0x10FFFF:
                out.append(0xF0 | (cp >> 18))
                out.append(0x80 | ((cp >> 12) & 0x3F))
                out.append(0x80 | ((cp >> 6) & 0x3F))
                out.append(0x80 | (cp & 0x3F))

            else:
                raise ValueError("invalid Unicode code point")

            i += 1

        return out

    def decode_bytes(self, values):
        if not isinstance(values, (list, tuple, bytes, bytearray)):
            raise TypeError("values must be byte sequence")

        data = list(values)
        chars = []
        i = 0

        while i < len(data):
            b0 = data[i]
            if not isinstance(b0, int) or b0 < 0 or b0 > 255:
                raise ValueError("byte value out of range")

            if b0 <= 0x7F:
                chars.append(chr(b0))
                i += 1
                continue

            if 0xC2 <= b0 <= 0xDF:
                needed = 2
                cp = b0 & 0x1F

            elif 0xE0 <= b0 <= 0xEF:
                needed = 3
                cp = b0 & 0x0F

            elif 0xF0 <= b0 <= 0xF4:
                needed = 4
                cp = b0 & 0x07

            else:
                raise ValueError("invalid UTF-8 leading byte at index " + str(i))

            if i + needed > len(data):
                raise ValueError("truncated UTF-8 sequence")

            j = 1
            while j < needed:
                bx = data[i + j]
                if bx < 0 or bx > 255 or (bx & 0xC0) != 0x80:
                    raise ValueError("invalid UTF-8 continuation byte")
                cp = (cp << 6) | (bx & 0x3F)
                j += 1

            if needed == 2 and cp < 0x80:
                raise ValueError("overlong UTF-8 sequence")
            if needed == 3 and cp < 0x800:
                raise ValueError("overlong UTF-8 sequence")
            if needed == 4 and cp < 0x10000:
                raise ValueError("overlong UTF-8 sequence")
            if 0xD800 <= cp <= 0xDFFF:
                raise ValueError("UTF-8 decoded surrogate")
            if cp > 0x10FFFF:
                raise ValueError("UTF-8 code point out of range")

            chars.append(chr(cp))
            i += needed

        return "".join(chars)
