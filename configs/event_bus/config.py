class EventBusConfig:
    def __init__(
        self,
        max_history=10000,
        subscriptions=None,
        metadata=None,
    ):
        if (
            not isinstance(
                max_history,
                int,
            )
            or max_history <= 0
        ):
            raise ValueError(
                "max_history must be positive int"
            )

        if subscriptions is None:
            subscriptions = []

        if not isinstance(
            subscriptions,
            (list, tuple),
        ):
            raise TypeError(
                "subscriptions must be list/tuple or None"
            )

        normalized = []
        seen = {}

        for subscription in subscriptions:
            if not isinstance(
                subscription,
                EventSubscriptionConfig,
            ):
                raise TypeError(
                    "subscription entries must be EventSubscriptionConfig"
                )

            if (
                subscription
                .subscription_id
                in seen
            ):
                raise ValueError(
                    "duplicate subscription_id: "
                    + subscription.subscription_id
                )

            seen[
                subscription
                .subscription_id
            ] = True

            normalized.append(
                subscription
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

        self.max_history = (
            max_history
        )
        self.subscriptions = (
            normalized
        )
        self.metadata = self._copy(
            metadata
        )

    def enabled_subscriptions(
        self,
    ):
        return [
            item
            for item
            in self.subscriptions
            if item.enabled
        ]

    def to_dict(
        self,
    ):
        return {
            "max_history": (
                self.max_history
            ),
            "subscriptions": [
                item.to_dict()
                for item
                in self.subscriptions
            ],
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
