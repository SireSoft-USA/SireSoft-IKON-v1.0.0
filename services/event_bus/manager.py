class EventBusManager:
    """
    In-process pub/sub event bus with ordered delivery and bounded history.

    Handler failures are isolated per subscriber; one failing subscriber does
    not stop later subscribers from receiving the same event.
    """

    def __init__(
        self,
        max_history=10000,
    ):
        if not isinstance(max_history, int) or max_history <= 0:
            raise ValueError("max_history must be positive int")

        self.max_history = max_history

        self._subscriptions = {}
        self._order = []
        self._history = []
        self._sequence = 0

        self.total_published = 0
        self.total_deliveries = 0
        self.total_failures = 0
        self.history_evictions = 0

    def subscribe(
        self,
        subscription_id,
        topic,
        handler,
        mode="exact",
        enabled=True,
        metadata=None,
    ):
        if subscription_id in self._subscriptions:
            raise ValueError(
                "subscription already exists: "
                + subscription_id
            )

        subscription = Subscription(
            subscription_id=subscription_id,
            topic=topic,
            handler=handler,
            mode=mode,
            enabled=enabled,
            metadata=metadata,
        )

        self._subscriptions[
            subscription_id
        ] = subscription

        self._order.append(
            subscription_id
        )

        return subscription

    def unsubscribe(
        self,
        subscription_id,
    ):
        subscription = self.get_subscription(
            subscription_id
        )

        del self._subscriptions[
            subscription_id
        ]

        self._order = [
            existing
            for existing in self._order
            if existing != subscription_id
        ]

        return subscription

    def get_subscription(
        self,
        subscription_id,
    ):
        if subscription_id not in self._subscriptions:
            raise KeyError(
                "subscription not found: "
                + str(subscription_id)
            )

        return self._subscriptions[
            subscription_id
        ]

    def list_subscriptions(self):
        return [
            self._subscriptions[
                subscription_id
            ].summary()
            for subscription_id in self._order
        ]

    def publish(
        self,
        topic,
        timestamp,
        payload=None,
        metadata=None,
        source_service=None,
        trace_id=None,
        correlation_id=None,
    ):
        if not isinstance(topic, str) or topic == "":
            raise ValueError("topic must be non-empty str")

        if not isinstance(timestamp, int) or timestamp < 0:
            raise ValueError("timestamp must be non-negative int")

        self._sequence += 1

        event = Event(
            event_id=(
                "event-"
                + str(self._sequence)
            ),
            topic=topic,
            sequence=self._sequence,
            timestamp=timestamp,
            payload=payload,
            metadata=metadata,
            source_service=source_service,
            trace_id=trace_id,
            correlation_id=correlation_id,
        )

        self._history.append(event)
        self.total_published += 1

        while len(self._history) > self.max_history:
            self._history.pop(0)
            self.history_evictions += 1

        deliveries = []

        for subscription_id in list(
            self._order
        ):
            subscription = self._subscriptions[
                subscription_id
            ]

            if not subscription.matches(
                topic
            ):
                continue

            try:
                result = subscription.handler(
                    event
                )

                subscription.delivered += 1
                self.total_deliveries += 1

                deliveries.append({
                    "subscription_id": (
                        subscription_id
                    ),
                    "success": True,
                    "result": self._safe_result(
                        result
                    ),
                    "error_type": None,
                    "error_message": None,
                })

            except Exception as error:
                subscription.failed += 1
                self.total_failures += 1

                deliveries.append({
                    "subscription_id": (
                        subscription_id
                    ),
                    "success": False,
                    "result": None,
                    "error_type": (
                        type(error).__name__
                    ),
                    "error_message": (
                        str(error)
                    ),
                })

        return {
            "event": event.to_dict(),
            "deliveries": deliveries,
            "delivery_count": len(
                deliveries
            ),
            "successful_deliveries": len([
                item
                for item in deliveries
                if item["success"]
            ]),
            "failed_deliveries": len([
                item
                for item in deliveries
                if not item["success"]
            ]),
        }

    def enable_subscription(
        self,
        subscription_id,
    ):
        return self.get_subscription(
            subscription_id
        ).enable()

    def disable_subscription(
        self,
        subscription_id,
    ):
        return self.get_subscription(
            subscription_id
        ).disable()

    def history(
        self,
        topic=None,
        minimum_sequence=None,
        limit=100,
        newest_first=False,
    ):
        if (
            not isinstance(
                limit,
                int,
            )
            or limit <= 0
        ):
            raise ValueError(
                "limit must be positive int"
            )

        records = list(
            self._history
        )

        if newest_first:
            records.reverse()

        result = []

        for event in records:
            if (
                topic is not None
                and event.topic
                != topic
            ):
                continue

            if (
                minimum_sequence
                is not None
                and event.sequence
                < minimum_sequence
            ):
                continue

            result.append(
                event.to_dict()
            )

            if len(result) >= limit:
                break

        return {
            "events": result,
            "count": len(result),
            "newest_first": bool(
                newest_first
            ),
        }

    def clear_history(self):
        count = len(
            self._history
        )

        self._history = []

        return {
            "cleared_events": count,
        }

    def status(self):
        enabled = 0
        disabled = 0

        for subscription_id in self._order:
            if self._subscriptions[
                subscription_id
            ].enabled:
                enabled += 1
            else:
                disabled += 1

        return {
            "ready": True,
            "subscription_count": len(
                self._order
            ),
            "enabled_subscriptions": enabled,
            "disabled_subscriptions": disabled,
            "history_count": len(
                self._history
            ),
            "max_history": self.max_history,
            "total_published": (
                self.total_published
            ),
            "total_deliveries": (
                self.total_deliveries
            ),
            "total_failures": (
                self.total_failures
            ),
            "history_evictions": (
                self.history_evictions
            ),
        }

    def _safe_result(
        self,
        value,
    ):
        if value is None:
            return None

        if isinstance(
            value,
            (str, int, float, bool),
        ):
            return value

        if isinstance(value, list):
            return [
                self._safe_result(
                    item
                )
                for item in value
            ]

        if isinstance(value, tuple):
            return [
                self._safe_result(
                    item
                )
                for item in value
            ]

        if isinstance(value, dict):
            result = {}

            for key in value:
                if not isinstance(
                    key,
                    str,
                ):
                    continue

                result[
                    key
                ] = self._safe_result(
                    value[key]
                )

            return result

        return {
            "type": (
                type(value).__name__
            ),
        }
