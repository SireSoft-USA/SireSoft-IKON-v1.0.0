class TextDocument:
    def __init__(self, content, source_name=None, line_count=0, character_count=0, byte_count=None):
        self.content = content
        self.source_name = source_name
        self.line_count = line_count
        self.character_count = character_count
        self.byte_count = byte_count

    def to_dict(self):
        return {
            "content": self.content,
            "source_name": self.source_name,
            "line_count": self.line_count,
            "character_count": self.character_count,
            "byte_count": self.byte_count,
        }


class TextParser:
    """
    Loss-preserving plain-text parser.
    No stripping, lowercasing, normalization, or rewriting is performed.
    """

    def parse(self, text, source_name=None, byte_count=None):
        if not isinstance(text, str):
            raise TypeError("text must be str")
        return TextDocument(
            content=text,
            source_name=source_name,
            line_count=self._count_lines(text),
            character_count=len(text),
            byte_count=byte_count,
        )

    def parse_bytes(self, data, codec=None, source_name=None):
        if not isinstance(data, (bytes, bytearray)):
            raise TypeError("data must be bytes or bytearray")
        raw = bytes(data)
        text = raw.decode("utf-8") if codec is None else codec.decode(raw)
        return self.parse(text, source_name=source_name, byte_count=len(raw))

    def parse_file(self, file_path, codec=None):
        handle = open(file_path, "rb")
        try:
            data = handle.read()
        finally:
            handle.close()
        return self.parse_bytes(data, codec=codec, source_name=file_path)

    def lines(self, text, keep_endings=False):
        if not isinstance(text, str):
            raise TypeError("text must be str")
        return text.splitlines(keepends=keep_endings)

    def paragraphs(self, text, preserve_empty=False):
        if not isinstance(text, str):
            raise TypeError("text must be str")

        lines = text.splitlines()
        result = []
        current = []

        for line in lines:
            if line.strip() == "":
                if current:
                    result.append("\n".join(current))
                    current = []
                elif preserve_empty:
                    result.append("")
            else:
                current.append(line)

        if current:
            result.append("\n".join(current))
        return result

    def _count_lines(self, text):
        if text == "":
            return 0
        count = 1
        for char in text:
            if char == "\n":
                count += 1
        return count
