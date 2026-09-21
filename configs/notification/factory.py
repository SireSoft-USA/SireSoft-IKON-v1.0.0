class NotificationConfigFactory:
    """
    Builds NotificationManager/Service from declarative templates/channels plus
    runtime-only transport handlers.
    """

    def build_manager(
        self,
        config,
        handlers,
        event_bus=None,
    ):
        if not isinstance(
            config,
            NotificationConfig,
        ):
            raise TypeError(
                "config must be NotificationConfig"
            )

        NotificationConfigValidator().require_valid(
            config
        )

        if not isinstance(
            handlers,
            dict,
        ):
            raise TypeError(
                "handlers must be dict"
            )

        if (
            config.attach_event_bus
            and event_bus is None
        ):
            raise ValueError(
                "notification config requires event_bus"
            )

        manager = NotificationManager(
            event_bus=(
                event_bus
                if config.attach_event_bus
                else None
            )
        )

        skipped_channels = []

        for item in config.channels:
            handler = self._resolve_handler(
                handlers,
                item,
            )

            if handler is None:
                skipped_channels.append(
                    item.channel_id
                )
                continue

            manager.register_channel(
                channel_id=(
                    item.channel_id
                ),
                handler=handler,
                enabled=item.enabled,
                metadata=item.metadata,
            )

        for template in (
            config.enabled_templates()
        ):
            manager.create_template(
                template_id=(
                    template.template_id
                ),
                body_template=(
                    template.body_template
                ),
                subject_template=(
                    template.subject_template
                ),
                metadata=(
                    template.metadata
                ),
            )

        return {
            "manager": manager,
            "registered_channel_count": (
                len(
                    manager.list_channels()
                )
            ),
            "registered_template_count": (
                len(
                    manager.list_templates()
                )
            ),
            "skipped_channel_ids": (
                skipped_channels
            ),
        }

    def build_service(
        self,
        config,
        handlers,
        event_bus=None,
    ):
        result = self.build_manager(
            config,
            handlers=handlers,
            event_bus=event_bus,
        )

        return NotificationService(
            result[
                "manager"
            ]
        )

    def _resolve_handler(
        self,
        handlers,
        item,
    ):
        if item.handler_key not in handlers:
            if item.required_handler:
                raise KeyError(
                    "missing notification handler: "
                    + item.handler_key
                    + " for channel "
                    + item.channel_id
                )

            return None

        candidate = handlers[
            item.handler_key
        ]

        if hasattr(
            candidate,
            "deliver",
        ):
            candidate = (
                candidate.deliver
            )

        elif hasattr(
            candidate,
            "send",
        ):
            candidate = (
                candidate.send
            )

        if not callable(
            candidate
        ):
            raise TypeError(
                "resolved notification handler must be callable or expose deliver()/send()"
            )

        return candidate
