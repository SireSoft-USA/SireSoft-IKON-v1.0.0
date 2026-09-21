class NotificationChannel:
    """
    Bound local delivery channel.

    The handler receives the Notification object. External email/SMS/webhook
    transports can later be implemented by runtime adapters without changing
    the notification-domain contract.
    """

    def __init__(
        self,
        channel_id,
        handler,
        enabled=True,
        metadata=None,
    ):
        if not isinstance(
            channel_id,
            str,
        ) or channel_id == "":
            raise ValueError(
                "channel_id must be non-empty str"
            )

        if not callable(
            handler
        ):
            raise TypeError(
                "handler must be callable"
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
        self.handler = handler
        self.enabled = bool(
            enabled
        )
        self.metadata = self._copy(
            metadata
        )

        self.delivered = 0
        self.failed = 0

    def deliver(
        self,
        notification,
    ):
        if not self.enabled:
            raise RuntimeError(
                "notification channel is disabled"
            )

        if not isinstance(
            notification,
            Notification,
        ):
            raise TypeError(
                "notification must be Notification"
            )

        try:
            result = self.handler(
                notification
            )

            self.delivered += 1

            return result

        except Exception:
            self.failed += 1
            raise

    def enable(
        self,
    ):
        self.enabled = True
        return self

    def disable(
        self,
    ):
        self.enabled = False
        return self

    def summary(
        self,
    ):
        return {
            "channel_id": (
                self.channel_id
            ),
            "enabled": self.enabled,
            "metadata": self._copy(
                self.metadata
            ),
            "delivered": (
                self.delivered
            ),
            "failed": (
                self.failed
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
            result = {}

            for key in value:
                result[
                    key
                ] = self._copy(
                    value[
                        key
                    ]
                )

            return result

        if isinstance(
            value,
            list,
        ):
            return [
                self._copy(
                    item
                )
                for item in value
            ]

        if isinstance(
            value,
            tuple,
        ):
            return [
                self._copy(
                    item
                )
                for item in value
            ]

        return value
