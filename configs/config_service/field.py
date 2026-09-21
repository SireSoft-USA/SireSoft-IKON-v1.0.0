class RuntimeConfigFieldConfig:
    def __init__(
        self,
        key,
        value_type,
        required=False,
        default=None,
        secret=False,
        choices=None,
        minimum=None,
        maximum=None,
        metadata=None,
    ):
        if (
            not isinstance(
                key,
                str,
            )
            or key == ""
        ):
            raise ValueError(
                "key must be non-empty str"
            )

        if value_type not in ConfigField.TYPES:
            raise ValueError(
                "unsupported config field value_type"
            )

        if choices is not None and not isinstance(
            choices,
            (list, tuple),
        ):
            raise TypeError(
                "choices must be list/tuple or None"
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

        self.key = key
        self.value_type = value_type
        self.required = bool(
            required
        )
        self.default = self._copy(
            default
        )
        self.secret = bool(
            secret
        )
        self.choices = (
            None
            if choices is None
            else list(
                choices
            )
        )
        self.minimum = minimum
        self.maximum = maximum
        self.metadata = self._copy(
            metadata
        )

        # Reuse the actual runtime validator now so config/schema cannot drift.
        self.to_runtime_field()

    def to_runtime_field(
        self,
    ):
        return ConfigField(
            key=self.key,
            value_type=self.value_type,
            required=self.required,
            default=self._copy(
                self.default
            ),
            secret=self.secret,
            choices=self._copy(
                self.choices
            ),
            minimum=self.minimum,
            maximum=self.maximum,
            metadata=self._copy(
                self.metadata
            ),
        )

    def to_dict(
        self,
    ):
        return {
            "key": self.key,
            "value_type": (
                self.value_type
            ),
            "required": (
                self.required
            ),
            "default": self._copy(
                self.default
            ),
            "secret": self.secret,
            "choices": self._copy(
                self.choices
            ),
            "minimum": self.minimum,
            "maximum": self.maximum,
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
