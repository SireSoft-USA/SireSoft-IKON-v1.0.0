class ConfigLayer:
    """
    One named configuration layer.

    Higher priority values override lower priority values.
    """

    def __init__(
        self,
        layer_id,
        priority,
        values=None,
        metadata=None,
    ):
        if not isinstance(
            layer_id,
            str,
        ) or layer_id == "":
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

    def set(
        self,
        key,
        value,
    ):
        self.values[
            key
        ] = self._copy(
            value
        )

        return self

    def unset(
        self,
        key,
    ):
        existed = key in self.values

        if existed:
            del self.values[
                key
            ]

        return existed

    def to_dict(
        self,
        redact_keys=None,
    ):
        if redact_keys is None:
            redact_keys = []

        values = {}

        for key in self.values:
            if key in redact_keys:
                values[
                    key
                ] = "[REDACTED]"
            else:
                values[
                    key
                ] = self._copy(
                    self.values[
                        key
                    ]
                )

        return {
            "layer_id": (
                self.layer_id
            ),
            "priority": (
                self.priority
            ),
            "values": values,
            "metadata": self._copy(
                self.metadata
            ),
        }

    def state_dict(
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
        }

    @classmethod
    def from_dict(
        cls,
        value,
    ):
        if not isinstance(
            value,
            dict,
        ):
            raise TypeError(
                "config layer state must be dict"
            )

        return cls(
            layer_id=value[
                "layer_id"
            ],
            priority=int(
                value[
                    "priority"
                ]
            ),
            values=value.get(
                "values",
                {},
            ),
            metadata=value.get(
                "metadata",
                {},
            ),
        )

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
