class ConfigField:
    TYPES = (
        "str",
        "int",
        "float",
        "bool",
        "list",
        "dict",
    )

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
        if not isinstance(
            key,
            str,
        ) or key == "":
            raise ValueError(
                "config key must be non-empty str"
            )

        if value_type not in self.TYPES:
            raise ValueError(
                "unsupported config value_type"
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

        if default is not None:
            self.validate(
                default
            )

    def validate(
        self,
        value,
    ):
        if value is None:
            if self.required:
                raise ValueError(
                    "required config value missing: "
                    + self.key
                )

            return True

        if not self._matches_type(
            value
        ):
            raise TypeError(
                "config value "
                + self.key
                + " must be "
                + self.value_type
            )

        if self.choices is not None:
            if value not in self.choices:
                raise ValueError(
                    "config value "
                    + self.key
                    + " is not an allowed choice"
                )

        if self.minimum is not None:
            if not isinstance(
                value,
                (int, float),
            ) or isinstance(
                value,
                bool,
            ):
                raise TypeError(
                    "minimum constraint requires numeric value"
                )

            if value < self.minimum:
                raise ValueError(
                    "config value "
                    + self.key
                    + " is below minimum"
                )

        if self.maximum is not None:
            if not isinstance(
                value,
                (int, float),
            ) or isinstance(
                value,
                bool,
            ):
                raise TypeError(
                    "maximum constraint requires numeric value"
                )

            if value > self.maximum:
                raise ValueError(
                    "config value "
                    + self.key
                    + " exceeds maximum"
                )

        return True

    def public_dict(
        self,
    ):
        return {
            "key": self.key,
            "value_type": (
                self.value_type
            ),
            "required": self.required,
            "default": (
                "[REDACTED]"
                if self.secret
                and self.default is not None
                else self._copy(
                    self.default
                )
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

    def state_dict(
        self,
    ):
        return {
            "key": self.key,
            "value_type": (
                self.value_type
            ),
            "required": self.required,
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
                "config field state must be dict"
            )

        return cls(
            key=value[
                "key"
            ],
            value_type=value[
                "value_type"
            ],
            required=value.get(
                "required",
                False,
            ),
            default=value.get(
                "default"
            ),
            secret=value.get(
                "secret",
                False,
            ),
            choices=value.get(
                "choices"
            ),
            minimum=value.get(
                "minimum"
            ),
            maximum=value.get(
                "maximum"
            ),
            metadata=value.get(
                "metadata",
                {},
            ),
        )

    def _matches_type(
        self,
        value,
    ):
        if self.value_type == "str":
            return isinstance(
                value,
                str,
            )

        if self.value_type == "int":
            return (
                isinstance(
                    value,
                    int,
                )
                and not isinstance(
                    value,
                    bool,
                )
            )

        if self.value_type == "float":
            return (
                isinstance(
                    value,
                    (int, float),
                )
                and not isinstance(
                    value,
                    bool,
                )
            )

        if self.value_type == "bool":
            return isinstance(
                value,
                bool,
            )

        if self.value_type == "list":
            return isinstance(
                value,
                list,
            )

        if self.value_type == "dict":
            return isinstance(
                value,
                dict,
            )

        return False

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


class ConfigSchema:
    def __init__(
        self,
        schema_id="default",
    ):
        if not isinstance(
            schema_id,
            str,
        ) or schema_id == "":
            raise ValueError(
                "schema_id must be non-empty str"
            )

        self.schema_id = schema_id
        self._fields = {}
        self._order = []

    def add_field(
        self,
        field,
    ):
        if not isinstance(
            field,
            ConfigField,
        ):
            raise TypeError(
                "field must be ConfigField"
            )

        if field.key in self._fields:
            raise ValueError(
                "duplicate config field: "
                + field.key
            )

        self._fields[
            field.key
        ] = field

        self._order.append(
            field.key
        )

        return self

    def get(
        self,
        key,
    ):
        if key not in self._fields:
            raise KeyError(
                "config field not found: "
                + str(
                    key
                )
            )

        return self._fields[
            key
        ]

    def contains(
        self,
        key,
    ):
        return key in self._fields

    def keys(
        self,
    ):
        return list(
            self._order
        )

    def defaults(
        self,
    ):
        result = {}

        for key in self._order:
            field = self._fields[
                key
            ]

            if field.default is not None:
                result[
                    key
                ] = field._copy(
                    field.default
                )

        return result

    def validate(
        self,
        values,
        reject_unknown=True,
    ):
        if not isinstance(
            values,
            dict,
        ):
            raise TypeError(
                "config values must be dict"
            )

        if reject_unknown:
            for key in values:
                if key not in self._fields:
                    raise ValueError(
                        "unknown config key: "
                        + str(
                            key
                        )
                    )

        for key in self._order:
            field = self._fields[
                key
            ]

            if key in values:
                field.validate(
                    values[
                        key
                    ]
                )

            elif (
                field.required
                and field.default is None
            ):
                raise ValueError(
                    "required config value missing: "
                    + key
                )

        return True

    def public_dict(
        self,
    ):
        return {
            "schema_id": (
                self.schema_id
            ),
            "fields": [
                self._fields[
                    key
                ].public_dict()
                for key in self._order
            ],
        }

    def state_dict(
        self,
    ):
        return {
            "schema_id": (
                self.schema_id
            ),
            "fields": [
                self._fields[
                    key
                ].state_dict()
                for key in self._order
            ],
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
                "config schema state must be dict"
            )

        schema = cls(
            value[
                "schema_id"
            ]
        )

        for field_state in value.get(
            "fields",
            [],
        ):
            schema.add_field(
                ConfigField.from_dict(
                    field_state
                )
            )

        return schema
