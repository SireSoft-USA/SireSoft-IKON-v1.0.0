class EventSubscriptionConfig:
    """
    Serializable event-bus subscription declaration.

    handler_key is a runtime dependency lookup key. Callable handlers are never
    serialized into configuration.
    """

    MODES = (
        "exact",
        "prefix",
    )

    def __init__(
        self,
        subscription_id,
        topic,
        handler_key,
        mode="exact",
        enabled=True,
        required_handler=True,
        metadata=None,
    ):
        if (
            not isinstance(
                subscription_id,
                str,
            )
            or subscription_id == ""
        ):
            raise ValueError(
                "subscription_id must be non-empty str"
            )

        if (
            not isinstance(
                topic,
                str,
            )
            or topic == ""
        ):
            raise ValueError(
                "topic must be non-empty str"
            )

        if (
            not isinstance(
                handler_key,
                str,
            )
            or handler_key == ""
        ):
            raise ValueError(
                "handler_key must be non-empty str"
            )

        if mode not in self.MODES:
            raise ValueError(
                "invalid subscription mode"
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

        self.subscription_id = (
            subscription_id
        )
        self.topic = topic
        self.handler_key = handler_key
        self.mode = mode
        self.enabled = bool(
            enabled
        )
        self.required_handler = bool(
            required_handler
        )
        self.metadata = self._copy(
            metadata
        )

    def to_dict(
        self,
    ):
        return {
            "subscription_id": (
                self.subscription_id
            ),
            "topic": self.topic,
            "handler_key": (
                self.handler_key
            ),
            "mode": self.mode,
            "enabled": (
                self.enabled
            ),
            "required_handler": (
                self.required_handler
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
