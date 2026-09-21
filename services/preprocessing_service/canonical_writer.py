class CanonicalJSONEncoder:
    """
    Minimal deterministic JSON serializer for canonical JSONL output.
    """

    def encode(self, value):
        if value is None:
            return "null"

        if value is True:
            return "true"

        if value is False:
            return "false"

        if isinstance(value, int):
            return str(value)

        if isinstance(value, float):
            return self._float_text(
                value
            )

        if isinstance(value, str):
            return self._string(
                value
            )

        if isinstance(value, (list, tuple)):
            pieces = []

            for item in value:
                pieces.append(
                    self.encode(
                        item
                    )
                )

            return (
                "["
                + ",".join(
                    pieces
                )
                + "]"
            )

        if isinstance(value, dict):
            keys = []

            for key in value:
                if not isinstance(key, str):
                    raise TypeError(
                        "JSON object keys must be strings"
                    )

                keys.append(
                    key
                )

            keys.sort()
            pieces = []

            for key in keys:
                pieces.append(
                    self._string(
                        key
                    )
                    + ":"
                    + self.encode(
                        value[key]
                    )
                )

            return (
                "{"
                + ",".join(
                    pieces
                )
                + "}"
            )

        raise TypeError(
            "unsupported JSON value type: "
            + type(value).__name__
        )

    def _float_text(self, value):
        text = repr(value)
        lower = text.lower()

        if lower in (
            "nan",
            "inf",
            "-inf",
            "infinity",
            "-infinity",
        ):
            raise ValueError(
                "non-finite floats are not valid canonical JSON"
            )

        return text

    def _string(self, value):
        pieces = ['"']

        for char in value:
            code = ord(char)

            if char == '"':
                pieces.append('\\"')
            elif char == "\\":
                pieces.append("\\\\")
            elif char == "\b":
                pieces.append("\\b")
            elif char == "\f":
                pieces.append("\\f")
            elif char == "\n":
                pieces.append("\\n")
            elif char == "\r":
                pieces.append("\\r")
            elif char == "\t":
                pieces.append("\\t")
            elif code < 32:
                pieces.append(
                    "\\u"
                    + self._hex4(
                        code
                    )
                )
            else:
                pieces.append(
                    char
                )

        pieces.append('"')

        return "".join(
            pieces
        )

    def _hex4(self, value):
        digits = "0123456789abcdef"
        result = ""
        shift = 12

        while shift >= 0:
            result += digits[
                (
                    value >> shift
                )
                & 0xF
            ]
            shift -= 4

        return result


class CanonicalJSONLWriter:
    """
    Streaming canonical-record exporter.
    """

    def __init__(self, encoder=None):
        self.encoder = (
            CanonicalJSONEncoder()
            if encoder is None
            else encoder
        )

    def write(
        self,
        records,
        output_path,
    ):
        if not isinstance(output_path, str) or output_path == "":
            raise ValueError(
                "output_path must be non-empty str"
            )

        writer = StreamWriter(
            output_path,
            mode="text",
        )

        count = 0

        with writer:
            for record in records:
                if not hasattr(
                    record,
                    "to_dict",
                ):
                    raise TypeError(
                        "record must provide to_dict()"
                    )

                writer.write_line(
                    self.encoder.encode(
                        record.to_dict()
                    )
                )

                count += 1

        return {
            "output_path": output_path,
            "record_count": count,
            "bytes_written": writer.bytes_written(),
        }
