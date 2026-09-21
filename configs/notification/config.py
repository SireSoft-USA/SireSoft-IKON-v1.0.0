class NotificationConfig:
    def __init__(
        self,
        channels,
        templates=None,
        attach_event_bus=False,
        metadata=None,
    ):
        if not isinstance(
            channels,
            (list, tuple),
        ) or len(
            channels
        ) == 0:
            raise ValueError(
                "channels must be non-empty list/tuple"
            )

        if templates is None:
            templates = []

        if not isinstance(
            templates,
            (list, tuple),
        ):
            raise TypeError(
                "templates must be list/tuple or None"
            )

        normalized_channels = []
        seen_channels = {}

        for channel in channels:
            if not isinstance(
                channel,
                NotificationChannelConfig,
            ):
                raise TypeError(
                    "channel entries must be NotificationChannelConfig"
                )

            if (
                channel.channel_id
                in seen_channels
            ):
                raise ValueError(
                    "duplicate notification channel_id: "
                    + channel.channel_id
                )

            seen_channels[
                channel.channel_id
            ] = True

            normalized_channels.append(
                channel
            )

        normalized_templates = []
        seen_templates = {}

        for template in templates:
            if not isinstance(
                template,
                NotificationTemplateConfig,
            ):
                raise TypeError(
                    "template entries must be NotificationTemplateConfig"
                )

            if (
                template.template_id
                in seen_templates
            ):
                raise ValueError(
                    "duplicate notification template_id: "
                    + template.template_id
                )

            seen_templates[
                template.template_id
            ] = True

            normalized_templates.append(
                template
            )

        if metadata is None:
            metadata = {}

        if not isinstance(
            metadata,
            dict,
        ):
            raise TypeError(
                "metadata must be dict or None"
            )

        self.channels = (
            normalized_channels
        )
        self.templates = (
            normalized_templates
        )
        self.attach_event_bus = bool(
            attach_event_bus
        )
        self.metadata = self._copy(
            metadata
        )

    def enabled_channels(
        self,
    ):
        return [
            item
            for item
            in self.channels
            if item.enabled
        ]

    def enabled_templates(
        self,
    ):
        return [
            item
            for item
            in self.templates
            if item.enabled
        ]

    def to_dict(
        self,
    ):
        return {
            "channels": [
                item.to_dict()
                for item
                in self.channels
            ],
            "templates": [
                item.to_dict()
                for item
                in self.templates
            ],
            "attach_event_bus": (
                self.attach_event_bus
            ),
            "metadata": self._copy(
                self.metadata
            ),
        }

    def _copy(
        self,
        value,
    ):
        if isinstance(
            value,
            dict,
        ):
            return {
                key: self._copy(
                    value[
                        key
                    ]
                )
                for key
                in value
            }

        if isinstance(
            value,
            (list, tuple),
        ):
            return [
                self._copy(
                    item
                )
                for item
                in value
            ]

        return value
