class ConversationDefaultsConfig:
    def __init__(
        self,
        system_message=None,
        title_prefix=None,
        metadata=None,
    ):
        if system_message is not None and (
            not isinstance(
                system_message,
                str,
            )
            or system_message == ""
        ):
            raise ValueError(
                "system_message must be non-empty str or None"
            )

        if title_prefix is not None and (
            not isinstance(
                title_prefix,
                str,
            )
            or title_prefix == ""
        ):
            raise ValueError(
                "title_prefix must be non-empty str or None"
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

        self.system_message = (
            system_message
        )
        self.title_prefix = (
            title_prefix
        )
        self.metadata = self._copy(
            metadata
        )

    def to_dict(
        self,
    ):
        return {
            "system_message": (
                self.system_message
            ),
            "title_prefix": (
                self.title_prefix
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
