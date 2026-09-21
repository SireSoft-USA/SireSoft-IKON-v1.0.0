class UnicodeRules:
    """
    Small, explicit Unicode compatibility layer implemented without unicodedata.

    This is deliberately conservative. Full Unicode normalization (NFC/NFKC)
    requires a large Unicode database. Instead of pretending otherwise, SireLLM
    uses explicit mappings for characters commonly encountered in web/dialogue
    corpora and preserves everything else unchanged.
    """

    def __init__(self):
        self._compatibility_map = {
            "\u00A0": " ",
            "\u2000": " ",
            "\u2001": " ",
            "\u2002": " ",
            "\u2003": " ",
            "\u2004": " ",
            "\u2005": " ",
            "\u2006": " ",
            "\u2007": " ",
            "\u2008": " ",
            "\u2009": " ",
            "\u200A": " ",
            "\u202F": " ",
            "\u205F": " ",
            "\u3000": " ",
            "\uFEFF": "",
            "\u200B": "",
            "\u200C": "",
            "\u200D": "",
            "\u2060": "",
            "\u00AD": "",
        }

    def normalize_compatibility(self, text):
        if not isinstance(text, str):
            raise TypeError("text must be str")

        out = []
        i = 0

        while i < len(text):
            char = text[i]

            if char in self._compatibility_map:
                out.append(self._compatibility_map[char])
            else:
                out.append(char)

            i += 1

        return "".join(out)

    def remove_disallowed_controls(self, text, keep_newline=True, keep_tab=True):
        if not isinstance(text, str):
            raise TypeError("text must be str")

        out = []
        i = 0

        while i < len(text):
            char = text[i]
            code = ord(char)

            allowed = True

            if code < 32:
                if char == "\n" and keep_newline:
                    allowed = True
                elif char == "\t" and keep_tab:
                    allowed = True
                elif char == "\r" and keep_newline:
                    allowed = True
                else:
                    allowed = False

            if code == 127:
                allowed = False

            if allowed:
                out.append(char)

            i += 1

        return "".join(out)

    def contains_surrogate(self, text):
        if not isinstance(text, str):
            raise TypeError("text must be str")

        i = 0
        while i < len(text):
            code = ord(text[i])
            if 0xD800 <= code <= 0xDFFF:
                return True
            i += 1

        return False

    def validate_scalar_values(self, text):
        if not isinstance(text, str):
            raise TypeError("text must be str")

        i = 0
        while i < len(text):
            code = ord(text[i])

            if 0xD800 <= code <= 0xDFFF:
                raise ValueError(
                    "text contains isolated Unicode surrogate at index " + str(i)
                )

            if code > 0x10FFFF:
                raise ValueError(
                    "text contains invalid Unicode code point at index " + str(i)
                )

            i += 1

        return True
