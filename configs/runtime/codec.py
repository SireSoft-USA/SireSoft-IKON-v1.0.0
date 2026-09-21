class RuntimeProfileCodec:
    """
    Decodes runtime profiles from the handwritten JSON parser already present
    in SireLLM. Encoding is deterministic and intentionally minimal.
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

    def decode_text(
        self,
        text,
    ):
        if not isinstance(text, str):
            raise TypeError(
                "profile text must be str"
            )

        value = self.parser.parse(
            text
        )

        if not isinstance(value, dict):
            raise ValueError(
                "runtime profile root must be object"
            )

        return self.from_dict(
            value
        )

    def from_dict(
        self,
        value,
    ):
        if not isinstance(value, dict):
            raise TypeError(
                "profile value must be dict"
            )

        required = (
            "name",
            "storage_root",
        )

        for key in required:
            if key not in value:
                raise ValueError(
                    "missing runtime profile field: "
                    + key
                )

        return RuntimeProfile(
            name=value[
                "name"
            ],
            storage_root=value[
                "storage_root"
            ],
            worker_count=value.get(
                "worker_count",
                4,
            ),
            queue_capacity=value.get(
                "queue_capacity",
                128,
            ),
            storage_namespaces=value.get(
                "storage_namespaces",
                [
                    "runtime",
                ],
            ),
            enable_signals=value.get(
                "enable_signals",
                True,
            ),
            host=value.get(
                "host",
                "127.0.0.1",
            ),
            port=value.get(
                "port",
                8080,
            ),
            backlog=value.get(
                "backlog",
                64,
            ),
            timeout_seconds=value.get(
                "timeout_seconds",
                5.0,
            ),
            recv_chunk_bytes=value.get(
                "recv_chunk_bytes",
                4096,
            ),
            max_requests=value.get(
                "max_requests"
            ),
            max_idle_timeouts=value.get(
                "max_idle_timeouts"
            ),
            metadata=value.get(
                "metadata",
                {},
            ),
        )

    def encode_text(
        self,
        profile,
    ):
        if not isinstance(
            profile,
            RuntimeProfile,
        ):
            raise TypeError(
                "profile must be RuntimeProfile"
            )

        return self._encode(
            profile.to_dict()
        )

    def _encode(
        self,
        value,
    ):
        if value is None:
            return "null"

        if value is True:
            return "true"

        if value is False:
            return "false"

        if isinstance(value, int):
            return str(
                value
            )

        if isinstance(value, float):
            text = repr(
                value
            )

            if (
                "nan" in text.lower()
                or "inf" in text.lower()
            ):
                raise ValueError(
                    "non-finite float is not supported"
                )

            return text

        if isinstance(value, str):
            return self._string(
                value
            )

        if isinstance(value, list):
            return (
                "["
                + ",".join(
                    self._encode(
                        item
                    )
                    for item
                    in value
                )
                + "]"
            )

        if isinstance(value, dict):
            keys = sorted(
                value.keys()
            )

            return (
                "{"
                + ",".join(
                    self._string(
                        str(
                            key
                        )
                    )
                    + ":"
                    + self._encode(
                        value[
                            key
                        ]
                    )
                    for key
                    in keys
                )
                + "}"
            )

        raise TypeError(
            "unsupported profile value"
        )

    def _string(
        self,
        value,
    ):
        result = '"'

        for character in value:
            code = ord(
                character
            )

            if character == '"':
                result += '\\"'

            elif character == "\\":
                result += "\\\\"

            elif character == "\b":
                result += "\\b"

            elif character == "\f":
                result += "\\f"

            elif character == "\n":
                result += "\\n"

            elif character == "\r":
                result += "\\r"

            elif character == "\t":
                result += "\\t"

            elif code < 32:
                result += (
                    "\\u"
                    + self._hex4(
                        code
                    )
                )

            else:
                result += character

        return result + '"'

    def _hex4(
        self,
        value,
    ):
        digits = (
            "0123456789abcdef"
        )

        output = ""

        shift = 12

        while shift >= 0:
            output += digits[
                (
                    value
                    >> shift
                )
                & 15
            ]

            shift -= 4

        return output
