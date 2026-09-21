class ConversationConfigCodec:
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
                "conversation config text must be str"
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
                "conversation config root must be object"
            )

        window = value.get(
            "window",
            {},
        )

        defaults = value.get(
            "defaults",
            {},
        )

        if not isinstance(
            window,
            dict,
        ):
            raise ValueError(
                "window section must be object"
            )

        if not isinstance(
            defaults,
            dict,
        ):
            raise ValueError(
                "defaults section must be object"
            )

        return ConversationConfig(
            window=(
                ConversationWindowConfig(
                    context_max_tokens=(
                        window.get(
                            "context_max_tokens",
                            256,
                        )
                    ),
                    rag_history_tokens=(
                        window.get(
                            "rag_history_tokens",
                            128,
                        )
                    ),
                )
            ),
            defaults=(
                ConversationDefaultsConfig(
                    system_message=(
                        defaults.get(
                            "system_message"
                        )
                    ),
                    title_prefix=(
                        defaults.get(
                            "title_prefix"
                        )
                    ),
                    metadata=(
                        defaults.get(
                            "metadata",
                            {},
                        )
                    ),
                )
            ),
            metadata=value.get(
                "metadata",
                {},
            ),
        )
