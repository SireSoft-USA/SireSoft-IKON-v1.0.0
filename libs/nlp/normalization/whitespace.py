class WhitespaceNormalizer:
    """
    Handwritten whitespace normalization rules.

    This class only creates a normalized representation. It never mutates or
    replaces the original source document stored by the data layer.
    """

    def normalize(
        self,
        text,
        collapse_spaces=True,
        trim_lines=True,
        collapse_blank_lines=True,
        preserve_newlines=True,
    ):
        if not isinstance(text, str):
            raise TypeError("text must be str")

        if preserve_newlines:
            return self._normalize_multiline(
                text,
                collapse_spaces,
                trim_lines,
                collapse_blank_lines,
            )

        return self._normalize_single_line(text, collapse_spaces, trim_lines)

    def _normalize_multiline(
        self,
        text,
        collapse_spaces,
        trim_lines,
        collapse_blank_lines,
    ):
        lines = self._split_newlines(text)
        out = []
        previous_blank = False

        for line in lines:
            normalized = line

            if collapse_spaces:
                normalized = self._collapse_horizontal_whitespace(normalized)

            if trim_lines:
                normalized = self._trim_horizontal(normalized)

            blank = normalized == ""

            if collapse_blank_lines and blank and previous_blank:
                continue

            out.append(normalized)
            previous_blank = blank

        return "\n".join(out)

    def _normalize_single_line(self, text, collapse_spaces, trim_lines):
        chars = []
        previous_space = False

        i = 0
        while i < len(text):
            char = text[i]

            if self._is_whitespace(char):
                if collapse_spaces:
                    if not previous_space:
                        chars.append(" ")
                    previous_space = True
                else:
                    chars.append(char)
                    previous_space = False
            else:
                chars.append(char)
                previous_space = False

            i += 1

        result = "".join(chars)

        if trim_lines:
            result = self._trim_horizontal(result)

        return result

    def _collapse_horizontal_whitespace(self, text):
        out = []
        previous_space = False

        i = 0
        while i < len(text):
            char = text[i]

            if self._is_horizontal_whitespace(char):
                if not previous_space:
                    out.append(" ")
                previous_space = True
            else:
                out.append(char)
                previous_space = False

            i += 1

        return "".join(out)

    def _trim_horizontal(self, text):
        start = 0
        end = len(text)

        while start < end and self._is_horizontal_whitespace(text[start]):
            start += 1

        while end > start and self._is_horizontal_whitespace(text[end - 1]):
            end -= 1

        return text[start:end]

    def _split_newlines(self, text):
        lines = []
        current = []
        i = 0

        while i < len(text):
            char = text[i]

            if char == "\r":
                if i + 1 < len(text) and text[i + 1] == "\n":
                    i += 1
                lines.append("".join(current))
                current = []

            elif char == "\n":
                lines.append("".join(current))
                current = []

            else:
                current.append(char)

            i += 1

        lines.append("".join(current))
        return lines

    def _is_horizontal_whitespace(self, char):
        return char == " " or char == "\t" or char == "\v" or char == "\f" or char == "\u00A0"

    def _is_whitespace(self, char):
        return (
            self._is_horizontal_whitespace(char)
            or char == "\n"
            or char == "\r"
        )
