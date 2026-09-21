class Subscription:
    """
    Event subscription with exact-topic or prefix matching.
    """

    MODES = (
        "exact",
        "prefix",
    )

    def __init__(
        self,
        subscription_id,
        topic,
        handler,
        mode="exact",
        enabled=True,
        metadata=None,
    ):
        if not isinstance(subscription_id, str) or subscription_id == "":
            raise ValueError("subscription_id must be non-empty str")

        if not isinstance(topic, str) or topic == "":
            raise ValueError("topic must be non-empty str")

        if not callable(handler):
            raise TypeError("handler must be callable")

        if mode not in self.MODES:
            raise ValueError("invalid subscription mode")

        if metadata is None:
            metadata = {}

        if not isinstance(metadata, dict):
            raise TypeError("metadata must be dict or None")

        self.subscription_id = subscription_id
        self.topic = topic
        self.handler = handler
        self.mode = mode
        self.enabled = bool(enabled)
        self.metadata = self._copy(metadata)

        self.delivered = 0
        self.failed = 0

    def matches(self, event_topic):
        if not self.enabled:
            return False

        if self.mode == "exact":
            return event_topic == self.topic

        return event_topic.startswith(
            self.topic
        )

    def enable(self):
        self.enabled = True
        return self

    def disable(self):
        self.enabled = False
        return self

    def summary(self):
        return {
            "subscription_id": self.subscription_id,
            "topic": self.topic,
            "mode": self.mode,
            "enabled": self.enabled,
            "metadata": self._copy(self.metadata),
            "delivered": self.delivered,
            "failed": self.failed,
        }

    def _copy(self, value):
        if isinstance(value, dict):
            result = {}
            for key in value:
                result[key] = self._copy(value[key])
            return result

        if isinstance(value, list):
            return [self._copy(item) for item in value]

        if isinstance(value, tuple):
            return [self._copy(item) for item in value]

        return value
