class JSONLParseError(ValueError):
    def __init__(self, message, line_number, source_name=None):
        self.line_number = line_number
        self.source_name = source_name
        prefix = "" if source_name is None else source_name + ":"
        ValueError.__init__(self, prefix + str(line_number) + ": " + message)


class JSONLParser:
    def __init__(self, json_parser):
        if json_parser is None or not hasattr(json_parser, "parse"):
            raise TypeError("json_parser must provide parse(text)")
        self._json_parser = json_parser

    def parse(self, text, skip_blank=True, source_name=None):
        if not isinstance(text, str):
            raise TypeError("JSONL input must be str")

        records = []
        lines = text.splitlines()
        line_number = 1

        for line in lines:
            candidate = line.strip()
            if candidate == "":
                if skip_blank:
                    line_number += 1
                    continue
                raise JSONLParseError("blank line encountered", line_number, source_name)

            try:
                records.append(self._json_parser.parse(candidate))
            except Exception as exc:
                raise JSONLParseError(str(exc), line_number, source_name)

            line_number += 1

        return records

    def parse_lines(self, lines, skip_blank=True, source_name=None):
        records = []
        line_number = 1

        for line in lines:
            if not isinstance(line, str):
                raise TypeError("all JSONL lines must be strings")
            candidate = line.strip()

            if candidate == "":
                if skip_blank:
                    line_number += 1
                    continue
                raise JSONLParseError("blank line encountered", line_number, source_name)

            try:
                records.append(self._json_parser.parse(candidate))
            except Exception as exc:
                raise JSONLParseError(str(exc), line_number, source_name)

            line_number += 1

        return records

    def iter_file(self, file_path, skip_blank=True, encoding="utf-8"):
        handle = open(file_path, "r", encoding=encoding)
        line_number = 0
        try:
            while True:
                line = handle.readline()
                if line == "":
                    break

                line_number += 1
                candidate = line.strip()

                if candidate == "":
                    if skip_blank:
                        continue
                    raise JSONLParseError("blank line encountered", line_number, file_path)

                try:
                    yield self._json_parser.parse(candidate)
                except Exception as exc:
                    raise JSONLParseError(str(exc), line_number, file_path)
        finally:
            handle.close()
