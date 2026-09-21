class UTF8Codec:
    """
    Strict UTF-8 encoder/decoder implemented from first principles.

    No codecs module and no third-party dependency is used.
    """

    def encode(self, text):
        if not isinstance(text, str):
            raise TypeError("text must be str")

        out = bytearray()
        i = 0

        while i < len(text):
            cp = ord(text[i])

            if 0xD800 <= cp <= 0xDFFF:
                raise UnicodeEncodeError(
                    "utf-8",
                    text,
                    i,
                    i + 1,
                    "surrogate code point is not valid UTF-8",
                )

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
                raise UnicodeEncodeError(
                    "utf-8",
                    text,
                    i,
                    i + 1,
                    "code point out of UTF-8 range",
                )

            i += 1

        return bytes(out)

    def decode(self, data):
        if isinstance(data, bytearray):
            data = bytes(data)
        if not isinstance(data, bytes):
            raise TypeError("data must be bytes or bytearray")

        chars = []
        i = 0
        n = len(data)

        while i < n:
            b0 = data[i]

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
                self._decode_error(data, i, i + 1, "invalid UTF-8 leading byte")

            if i + needed > n:
                self._decode_error(data, i, n, "truncated UTF-8 sequence")

            j = 1
            while j < needed:
                bx = data[i + j]
                if (bx & 0xC0) != 0x80:
                    self._decode_error(
                        data,
                        i + j,
                        i + j + 1,
                        "invalid UTF-8 continuation byte",
                    )
                cp = (cp << 6) | (bx & 0x3F)
                j += 1

            if needed == 2 and cp < 0x80:
                self._decode_error(data, i, i + needed, "overlong UTF-8 sequence")
            if needed == 3 and cp < 0x800:
                self._decode_error(data, i, i + needed, "overlong UTF-8 sequence")
            if needed == 4 and cp < 0x10000:
                self._decode_error(data, i, i + needed, "overlong UTF-8 sequence")

            if 0xD800 <= cp <= 0xDFFF:
                self._decode_error(data, i, i + needed, "UTF-8 decoded surrogate")
            if cp > 0x10FFFF:
                self._decode_error(data, i, i + needed, "UTF-8 code point out of range")

            chars.append(chr(cp))
            i += needed

        return "".join(chars)

    def _decode_error(self, data, start, end, reason):
        raise UnicodeDecodeError("utf-8", data, start, end, reason)
