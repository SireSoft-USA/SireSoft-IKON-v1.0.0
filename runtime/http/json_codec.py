class RuntimeJSONCodec:
    """
    Uses the handwritten Folder 05 JSONParser and a small deterministic JSON
    serializer for HTTP transport payloads.
    """

    def __init__(
        self,
        parser=None,
    ):
        self.parser = (
            JSONParser()
            if parser is None
            else parser
        )

    def decode(
        self,
        data,
    ):
        if not isinstance(
            data,
            (bytes, bytearray),
        ):
            raise TypeError(
                "JSON HTTP body must be bytes-like"
            )

        raw = bytes(
            data
        )

        try:
            text = raw.decode(
                "utf-8"
            )

        except UnicodeDecodeError:
            raise ValueError(
                "JSON HTTP body must be UTF-8"
            )

        return self.parser.parse(
            text
        )

    def encode(
        self,
        value,
    ):
        return self._encode_value(
            value
        ).encode(
            "utf-8"
        )

    def _encode_value(
        self,
        value,
    ):
        if value is None:
            return "null"

        if value is True:
            return "true"

        if value is False:
            return "false"

        if isinstance(
            value,
            int,
        ):
            return str(
                value
            )

        if isinstance(
            value,
            float,
        ):
            if value != value:
                raise ValueError(
                    "NaN is not valid JSON"
                )

            positive_infinity = float(
                "inf"
            )

            if (
                value == positive_infinity
                or value == -positive_infinity
            ):
                raise ValueError(
                    "infinite values are not valid JSON"
                )

            return repr(
                value
            )

        if isinstance(
            value,
            str,
        ):
            return self._encode_string(
                value
            )

        if isinstance(
            value,
            (list, tuple),
        ):
            return (
                "["
                + ",".join(
                    [
                        self._encode_value(
                            item
                        )
                        for item
                        in value
                    ]
                )
                + "]"
            )

        if isinstance(
            value,
            dict,
        ):
            parts = []

            for key in value:
                if not isinstance(
                    key,
                    str,
                ):
                    raise TypeError(
                        "JSON object keys must be strings"
                    )

                parts.append(
                    self._encode_string(
                        key
                    )
                    + ":"
                    + self._encode_value(
                        value[
                            key
                        ]
                    )
                )

            return (
                "{"
                + ",".join(
                    parts
                )
                + "}"
            )

        raise TypeError(
            "unsupported JSON value type: "
            + type(
                value
            ).__name__
        )

    def _encode_string(
        self,
        value,
    ):
        parts = [
            '"'
        ]

        for character in value:
            code = ord(
                character
            )

            if character == '"':
                parts.append(
                    '\\"'
                )

            elif character == "\\":
                parts.append(
                    "\\\\"
                )

            elif character == "\b":
                parts.append(
                    "\\b"
                )

            elif character == "\f":
                parts.append(
                    "\\f"
                )

            elif character == "\n":
                parts.append(
                    "\\n"
                )

            elif character == "\r":
                parts.append(
                    "\\r"
                )

            elif character == "\t":
                parts.append(
                    "\\t"
                )

            elif code < 0x20:
                hexadecimal = hex(
                    code
                )[2:].upper()

                parts.append(
                    "\\u"
                    + (
                        "0"
                        * (
                            4
                            - len(
                                hexadecimal
                            )
                        )
                    )
                    + hexadecimal
                )

            else:
                parts.append(
                    character
                )

        parts.append(
            '"'
        )

        return "".join(
            parts
        )
