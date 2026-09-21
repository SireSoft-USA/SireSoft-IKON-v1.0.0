class NotificationChannelConfig:
    """
    Serializable notification channel declaration.

    handler_key resolves to a runtime callable. Provider credentials, sockets,
    email clients, HTTP adapters, or other transport objects are deliberately
    excluded from configuration.
    """

    def __init__(
        self,
        channel_id,
        handler_key,
        enabled=True,
        required_handler=True,
        metadata=None,
    ):
        if (
            not isinstance(
                channel_id,
                str,
            )
            or channel_id == ""
        ):
            raise ValueError(
                "channel_id must be non-empty str"
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

        if metadata is None:
            metadata = {}

        if not isinstance(
            metadata,
            dict,
        ):
            raise TypeError(
                "metadata must be dict or None"
            )

        self.channel_id = (
            channel_id
        )
        self.handler_key = (
            handler_key
        )
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
            "channel_id": (
                self.channel_id
            ),
            "handler_key": (
                self.handler_key
            ),
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
