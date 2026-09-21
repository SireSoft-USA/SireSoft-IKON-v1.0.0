class EventBusConfigCodec:
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
                "event bus config text must be str"
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
                "event bus config root must be object"
            )

        raw_subscriptions = value.get(
            "subscriptions",
            [],
        )

        if not isinstance(
            raw_subscriptions,
            list,
        ):
            raise ValueError(
                "subscriptions must be list"
            )

        subscriptions = []

        for raw in raw_subscriptions:
            if not isinstance(
                raw,
                dict,
            ):
                raise ValueError(
                    "event subscription config must be object"
                )

            subscriptions.append(
                EventSubscriptionConfig(
                    subscription_id=(
                        raw.get(
                            "subscription_id"
                        )
                    ),
                    topic=raw.get(
                        "topic"
                    ),
                    handler_key=(
                        raw.get(
                            "handler_key"
                        )
                    ),
                    mode=raw.get(
                        "mode",
                        "exact",
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

        return EventBusConfig(
            max_history=value.get(
                "max_history",
                10000,
            ),
            subscriptions=(
                subscriptions
            ),
            metadata=value.get(
                "metadata",
                {},
            ),
        )
