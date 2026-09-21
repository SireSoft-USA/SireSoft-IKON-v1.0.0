class RuntimeConfigLayerConfig:
    def __init__(
        self,
        layer_id,
        priority,
        values=None,
        metadata=None,
        enabled=True,
    ):
        if (
            not isinstance(
                layer_id,
                str,
            )
            or layer_id == ""
        ):
            raise ValueError(
                "layer_id must be non-empty str"
            )

        if not isinstance(
            priority,
            int,
        ):
            raise TypeError(
                "priority must be int"
            )

        if values is None:
            values = {}

        if metadata is None:
            metadata = {}

        if not isinstance(
            values,
            dict,
        ):
            raise TypeError(
                "values must be dict or None"
            )

        if not isinstance(
            metadata,
            dict,
        ):
            raise TypeError(
                "metadata must be dict or None"
            )

        self.layer_id = layer_id
        self.priority = priority
        self.values = self._copy(
            values
        )
        self.metadata = self._copy(
            metadata
        )
        self.enabled = bool(
            enabled
        )

    def to_dict(
        self,
    ):
        return {
            "layer_id": (
                self.layer_id
            ),
            "priority": (
                self.priority
            ),
            "values": self._copy(
                self.values
            ),
            "metadata": self._copy(
                self.metadata
            ),
            "enabled": (
                self.enabled
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
