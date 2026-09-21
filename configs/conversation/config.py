class ConversationConfig:
    def __init__(
        self,
        window=None,
        defaults=None,
        metadata=None,
    ):
        if window is None:
            window = (
                ConversationWindowConfig()
            )

        if defaults is None:
            defaults = (
                ConversationDefaultsConfig()
            )

        if not isinstance(
            window,
            ConversationWindowConfig,
        ):
            raise TypeError(
                "window must be ConversationWindowConfig"
            )

        if not isinstance(
            defaults,
            ConversationDefaultsConfig,
        ):
            raise TypeError(
                "defaults must be ConversationDefaultsConfig"
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

        self.window = window
        self.defaults = defaults
        self.metadata = self._copy(
            metadata
        )

    def to_dict(
        self,
    ):
        return {
            "window": (
                self.window.to_dict()
            ),
            "defaults": (
                self.defaults.to_dict()
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
