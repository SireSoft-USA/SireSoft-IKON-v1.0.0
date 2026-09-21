class LoggingConfigCodec:
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
        if not isinstance(
            text,
            str,
        ):
            raise TypeError(
                "logging config text must be str"
            )

        return self.from_dict(
            self.parser.parse(
                text
            )
        )

    def from_dict(
        self,
        value,
    ):
        if not isinstance(
            value,
            dict,
        ):
            raise ValueError(
                "logging config root must be object"
            )

        raw_sinks = value.get(
            "sinks",
            [
                {
                    "sink_id": "memory",
                    "max_records": 10000,
                    "enabled": True,
                },
            ],
        )

        if not isinstance(
            raw_sinks,
            list,
        ) or len(
            raw_sinks
        ) == 0:
            raise ValueError(
                "sinks must be non-empty list"
            )

        sinks = []

        for raw in raw_sinks:
            if not isinstance(
                raw,
                dict,
            ):
                raise ValueError(
                    "logging sink entry must be object"
                )

            sinks.append(
                LogSinkConfig(
                    sink_id=raw.get(
                        "sink_id"
                    ),
                    max_records=raw.get(
                        "max_records",
                        10000,
                    ),
                    enabled=raw.get(
                        "enabled",
                        True,
                    ),
                    metadata=raw.get(
                        "metadata",
                        {},
                    ),
                )
            )

        return LoggingConfig(
            minimum_level=value.get(
                "minimum_level",
                "INFO",
            ),
            sinks=sinks,
            archive_path=value.get(
                "archive_path"
            ),
            metadata=value.get(
                "metadata",
                {},
            ),
        )
