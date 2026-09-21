class NotificationConfigCodec:
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
                "notification config text must be str"
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
                "notification config root must be object"
            )

        raw_channels = value.get(
            "channels"
        )

        raw_templates = value.get(
            "templates",
            [],
        )

        if not isinstance(
            raw_channels,
            list,
        ) or len(
            raw_channels
        ) == 0:
            raise ValueError(
                "channels must be non-empty list"
            )

        if not isinstance(
            raw_templates,
            list,
        ):
            raise ValueError(
                "templates must be list"
            )

        channels = []

        for raw in raw_channels:
            if not isinstance(
                raw,
                dict,
            ):
                raise ValueError(
                    "notification channel config must be object"
                )

            channels.append(
                NotificationChannelConfig(
                    channel_id=raw.get(
                        "channel_id"
                    ),
                    handler_key=raw.get(
                        "handler_key"
                    ),
                    enabled=raw.get(
                        "enabled",
                        True,
                    ),
                    required_handler=(
                        raw.get(
                            "required_handler",
                            True,
                        )
                    ),
                    metadata=raw.get(
                        "metadata",
                        {},
                    ),
                )
            )

        templates = []

        for raw in raw_templates:
            if not isinstance(
                raw,
                dict,
            ):
                raise ValueError(
                    "notification template config must be object"
                )

            templates.append(
                NotificationTemplateConfig(
                    template_id=(
                        raw.get(
                            "template_id"
                        )
                    ),
                    body_template=(
                        raw.get(
                            "body_template",
                            "",
                        )
                    ),
                    subject_template=(
                        raw.get(
                            "subject_template"
                        )
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

        return NotificationConfig(
            channels=channels,
            templates=templates,
            attach_event_bus=(
                value.get(
                    "attach_event_bus",
                    False,
                )
            ),
            metadata=value.get(
                "metadata",
                {},
            ),
        )
