class EventBusConfigFactory:
    """
    Resolves runtime-only subscription handlers and builds the real in-process
    EventBusManager / EventBusService.
    """

    def build_manager(
        self,
        config,
        handlers=None,
    ):
        if not isinstance(
            config,
            EventBusConfig,
        ):
            raise TypeError(
                "config must be EventBusConfig"
            )

        EventBusConfigValidator().require_valid(
            config
        )

        if handlers is None:
            handlers = {}

        if not isinstance(
            handlers,
            dict,
        ):
            raise TypeError(
                "handlers must be dict or None"
            )

        manager = EventBusManager(
            max_history=(
                config.max_history
            )
        )

        skipped = []

        for item in config.subscriptions:
            handler = self._resolve_handler(
                handlers,
                item,
            )

            if handler is None:
                skipped.append(
                    item.subscription_id
                )
                continue

            manager.subscribe(
                subscription_id=(
                    item.subscription_id
                ),
                topic=item.topic,
                handler=handler,
                mode=item.mode,
                enabled=item.enabled,
                metadata=item.metadata,
            )

        return {
            "manager": manager,
            "registered_count": (
                len(
                    manager
                    .list_subscriptions()
                )
            ),
            "skipped_subscription_ids": (
                skipped
            ),
        }

    def build_service(
        self,
        config,
        handlers=None,
    ):
        result = self.build_manager(
            config,
            handlers=handlers,
        )

        return EventBusService(
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
                    "missing event handler: "
                    + item.handler_key
                    + " for subscription "
                    + item.subscription_id
                )

            return None

        candidate = handlers[
            item.handler_key
        ]

        if hasattr(
            candidate,
            "handle_event",
        ):
            candidate = (
                candidate
                .handle_event
            )

        elif hasattr(
            candidate,
            "handle",
        ):
            candidate = (
                candidate.handle
            )

        if not callable(
            candidate
        ):
            raise TypeError(
                "resolved event handler must be callable or expose handle_event()/handle()"
            )

        return candidate
