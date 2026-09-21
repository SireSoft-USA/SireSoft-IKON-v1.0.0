class JSONParseError(ValueError):
    def __init__(self, message, position, line, column):
        self.message = message
        self.position = position
        self.line = line
        self.column = column
        ValueError.__init__(self, message + " at line " + str(line) + ", column " + str(column))


class JSONParser:
    def __init__(self):
        self._text = ""
        self._length = 0
        self._index = 0
        self._line = 1
        self._column = 1

    def parse(self, text):
        if not isinstance(text, str):
            raise TypeError("JSON input must be str")
        self._text = text
        self._length = len(text)
        self._index = 0
        self._line = 1
        self._column = 1

        self._skip_whitespace()
        value = self._parse_value()
        self._skip_whitespace()

        if self._index != self._length:
            self._error("unexpected trailing content")
        return value

    def _current(self):
        if self._index >= self._length:
            return None
        return self._text[self._index]

    def _advance(self):
        if self._index >= self._length:
            return None
        char = self._text[self._index]
        self._index += 1
        if char == "\n":
            self._line += 1
            self._column = 1
        else:
            self._column += 1
        return char

    def _error(self, message):
        raise JSONParseError(message, self._index, self._line, self._column)

    def _skip_whitespace(self):
        while self._index < self._length:
            char = self._text[self._index]
            if char == " " or char == "\t" or char == "\r" or char == "\n":
                self._advance()
            else:
                break

    def _parse_value(self):
        char = self._current()
        if char is None:
            self._error("expected JSON value")
        if char == "{":
            return self._parse_object()
        if char == "[":
            return self._parse_array()
        if char == '"':
            return self._parse_string()
        if char == "t":
            return self._parse_literal("true", True)
        if char == "f":
            return self._parse_literal("false", False)
        if char == "n":
            return self._parse_literal("null", None)
        if char == "-" or ("0" <= char <= "9"):
            return self._parse_number()
        self._error("invalid JSON value")

    def _parse_literal(self, literal, value):
        i = 0
        while i < len(literal):
            if self._current() != literal[i]:
                self._error("invalid literal")
            self._advance()
            i += 1
        return value

    def _parse_object(self):
        result = {}
        self._advance()
        self._skip_whitespace()
        if self._current() == "}":
            self._advance()
            return result

        while True:
            if self._current() != '"':
                self._error("object keys must be strings")
            key = self._parse_string()
            self._skip_whitespace()
            if self._current() != ":":
                self._error("expected ':' after object key")
            self._advance()
            self._skip_whitespace()
            result[key] = self._parse_value()
            self._skip_whitespace()

            char = self._current()
            if char == "}":
                self._advance()
                return result
            if char != ",":
                self._error("expected ',' or '}' in object")
            self._advance()
            self._skip_whitespace()
            if self._current() == "}":
                self._error("trailing comma is not valid JSON")

    def _parse_array(self):
        result = []
        self._advance()
        self._skip_whitespace()
        if self._current() == "]":
            self._advance()
            return result

        while True:
            result.append(self._parse_value())
            self._skip_whitespace()
            char = self._current()
            if char == "]":
                self._advance()
                return result
            if char != ",":
                self._error("expected ',' or ']' in array")
            self._advance()
            self._skip_whitespace()
            if self._current() == "]":
                self._error("trailing comma is not valid JSON")

    def _parse_string(self):
        if self._current() != '"':
            self._error("expected string")
        self._advance()
        chars = []

        while True:
            char = self._current()
            if char is None:
                self._error("unterminated string")
            if char == '"':
                self._advance()
                return "".join(chars)
            if ord(char) < 0x20:
                self._error("unescaped control character in string")
            if char != "\\":
                chars.append(char)
                self._advance()
                continue

            self._advance()
            escape = self._current()
            if escape is None:
                self._error("unterminated escape sequence")

            if escape == '"':
                chars.append('"')
                self._advance()
            elif escape == "\\":
                chars.append("\\")
                self._advance()
            elif escape == "/":
                chars.append("/")
                self._advance()
            elif escape == "b":
                chars.append("\b")
                self._advance()
            elif escape == "f":
                chars.append("\f")
                self._advance()
            elif escape == "n":
                chars.append("\n")
                self._advance()
            elif escape == "r":
                chars.append("\r")
                self._advance()
            elif escape == "t":
                chars.append("\t")
                self._advance()
            elif escape == "u":
                chars.append(self._parse_unicode_escape())
            else:
                self._error("invalid string escape")

    def _parse_unicode_escape(self):
        self._advance()
        code_unit = self._read_hex4()

        if 0xD800 <= code_unit <= 0xDBFF:
            if self._current() != "\\":
                self._error("high surrogate must be followed by low surrogate")
            self._advance()
            if self._current() != "u":
                self._error("high surrogate must be followed by Unicode escape")
            self._advance()
            low = self._read_hex4()
            if not (0xDC00 <= low <= 0xDFFF):
                self._error("invalid low surrogate")
            codepoint = 0x10000 + ((code_unit - 0xD800) << 10) + (low - 0xDC00)
            return chr(codepoint)

        if 0xDC00 <= code_unit <= 0xDFFF:
            self._error("unexpected low surrogate")
        return chr(code_unit)

    def _read_hex4(self):
        value = 0
        count = 0
        while count < 4:
            char = self._current()
            if char is None:
                self._error("incomplete Unicode escape")
            digit = self._hex_value(char)
            if digit < 0:
                self._error("invalid hexadecimal digit in Unicode escape")
            value = (value << 4) | digit
            self._advance()
            count += 1
        return value

    def _hex_value(self, char):
        if "0" <= char <= "9":
            return ord(char) - ord("0")
        if "a" <= char <= "f":
            return 10 + ord(char) - ord("a")
        if "A" <= char <= "F":
            return 10 + ord(char) - ord("A")
        return -1

    def _parse_number(self):
        start = self._index

        if self._current() == "-":
            self._advance()

        char = self._current()
        if char is None:
            self._error("incomplete number")

        if char == "0":
            self._advance()
            nxt = self._current()
            if nxt is not None and "0" <= nxt <= "9":
                self._error("leading zero is not valid JSON number")
        elif "1" <= char <= "9":
            while True:
                char = self._current()
                if char is not None and "0" <= char <= "9":
                    self._advance()
                else:
                    break
        else:
            self._error("invalid number")

        is_float = False

        if self._current() == ".":
            is_float = True
            self._advance()
            char = self._current()
            if char is None or not ("0" <= char <= "9"):
                self._error("fraction requires at least one digit")
            while True:
                char = self._current()
                if char is not None and "0" <= char <= "9":
                    self._advance()
                else:
                    break

        char = self._current()
        if char == "e" or char == "E":
            is_float = True
            self._advance()
            char = self._current()
            if char == "+" or char == "-":
                self._advance()
            char = self._current()
            if char is None or not ("0" <= char <= "9"):
                self._error("exponent requires at least one digit")
            while True:
                char = self._current()
                if char is not None and "0" <= char <= "9":
                    self._advance()
                else:
                    break

        token = self._text[start:self._index]
        try:
            return float(token) if is_float else int(token)
        except ValueError:
            self._error("invalid number")


def parse_json(text):
    return JSONParser().parse(text)
