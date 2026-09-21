class ConfigManager:
    """
    Layered runtime configuration manager.

    Resolution order:
      schema defaults
      -> lower-priority layers
      -> higher-priority layers

    Same-priority layers resolve in insertion order, with later layers winning.
    """

    REDACTED = "[REDACTED]"

    def __init__(
        self,
        schema=None,
        persistence=None,
    ):
        self.schema = (
            ConfigSchema()
            if schema is None
            else schema
        )

        if not isinstance(
            self.schema,
            ConfigSchema,
        ):
            raise TypeError(
                "schema must be ConfigSchema"
            )

        self.persistence = (
            ConfigPersistence()
            if persistence is None
            else persistence
        )

        self._layers = {}
        self._order = []
        self.version = 0

    def add_layer(
        self,
        layer_id,
        priority,
        values=None,
        metadata=None,
    ):
        if layer_id in self._layers:
            raise ValueError(
                "config layer already exists: "
                + str(
                    layer_id
                )
            )

        layer = ConfigLayer(
            layer_id=layer_id,
            priority=priority,
            values=values,
            metadata=metadata,
        )

        self._validate_partial(
            layer.values
        )

        self._layers[
            layer_id
        ] = layer

        self._order.append(
            layer_id
        )

        self._validate_resolved()

        self.version += 1

        return layer

    def remove_layer(
        self,
        layer_id,
    ):
        layer = self.get_layer(
            layer_id
        )

        old_order = list(
            self._order
        )

        del self._layers[
            layer_id
        ]

        self._order = [
            existing
            for existing in self._order
            if existing != layer_id
        ]

        try:
            self._validate_resolved()

        except Exception:
            self._layers[
                layer_id
            ] = layer
            self._order = old_order
            raise

        self.version += 1

        return layer

    def get_layer(
        self,
        layer_id,
    ):
        if layer_id not in self._layers:
            raise KeyError(
                "config layer not found: "
                + str(
                    layer_id
                )
            )

        return self._layers[
            layer_id
        ]

    def set_value(
        self,
        layer_id,
        key,
        value,
    ):
        layer = self.get_layer(
            layer_id
        )

        if not self.schema.contains(
            key
        ):
            raise ValueError(
                "unknown config key: "
                + str(
                    key
                )
            )

        self.schema.get(
            key
        ).validate(
            value
        )

        existed = key in layer.values
        old_value = None

        if existed:
            old_value = layer._copy(
                layer.values[
                    key
                ]
            )

        layer.set(
            key,
            value,
        )

        try:
            self._validate_resolved()

        except Exception:
            if existed:
                layer.set(
                    key,
                    old_value,
                )
            else:
                layer.unset(
                    key
                )

            raise

        self.version += 1

        return self.public_get(
            key
        )

    def unset_value(
        self,
        layer_id,
        key,
    ):
        layer = self.get_layer(
            layer_id
        )

        if key not in layer.values:
            return False

        old_value = layer._copy(
            layer.values[
                key
            ]
        )

        layer.unset(
            key
        )

        try:
            self._validate_resolved()

        except Exception:
            layer.set(
                key,
                old_value,
            )
            raise

        self.version += 1

        return True

    def resolve_internal(
        self,
    ):
        result = self.schema.defaults()

        ordered_layers = self._sorted_layers()

        for layer in ordered_layers:
            for key in layer.values:
                result[
                    key
                ] = layer._copy(
                    layer.values[
                        key
                    ]
                )

        self.schema.validate(
            result,
            reject_unknown=True,
        )

        return result

    def resolve_public(
        self,
    ):
        resolved = self.resolve_internal()

        result = {}

        for key in resolved:
            field = self.schema.get(
                key
            )

            if field.secret:
                result[
                    key
                ] = self.REDACTED
            else:
                result[
                    key
                ] = self._copy(
                    resolved[
                        key
                    ]
                )

        return result

    def get_internal(
        self,
        key,
    ):
        resolved = self.resolve_internal()

        if key not in resolved:
            raise KeyError(
                "config value not resolved: "
                + str(
                    key
                )
            )

        return self._copy(
            resolved[
                key
            ]
        )

    def public_get(
        self,
        key,
    ):
        if not self.schema.contains(
            key
        ):
            raise KeyError(
                "config field not found: "
                + str(
                    key
                )
            )

        field = self.schema.get(
            key
        )

        resolved = self.resolve_internal()

        if key not in resolved:
            raise KeyError(
                "config value not resolved: "
                + str(
                    key
                )
            )

        return {
            "key": key,
            "value": (
                self.REDACTED
                if field.secret
                else self._copy(
                    resolved[
                        key
                    ]
                )
            ),
            "secret": (
                field.secret
            ),
            "source_layer": (
                self.source_layer(
                    key
                )
            ),
        }

    def source_layer(
        self,
        key,
    ):
        if not self.schema.contains(
            key
        ):
            raise KeyError(
                "config field not found: "
                + str(
                    key
                )
            )

        source = (
            "schema_default"
            if self.schema.get(
                key
            ).default
            is not None
            else None
        )

        for layer in self._sorted_layers():
            if key in layer.values:
                source = (
                    layer.layer_id
                )

        return source

    def list_layers(
        self,
    ):
        secret_keys = [
            key
            for key in self.schema.keys()
            if self.schema.get(
                key
            ).secret
        ]

        return [
            layer.to_dict(
                redact_keys=(
                    secret_keys
                )
            )
            for layer in self._sorted_layers()
        ]

    def validate(
        self,
    ):
        self._validate_resolved()

        return {
            "valid": True,
            "version": (
                self.version
            ),
            "resolved_keys": len(
                self.resolve_internal()
            ),
        }

    def save_state(
        self,
        path,
    ):
        return self.persistence.save(
            path,
            self,
        )

    def load_state_file(
        self,
        path,
    ):
        return self.persistence.load(
            path,
            self,
        )

    def export_state(
        self,
        include_secrets=False,
    ):
        schema_state = (
            self.schema.state_dict()
            if include_secrets
            else self.schema.public_dict()
        )

        secret_keys = [
            key
            for key in self.schema.keys()
            if self.schema.get(
                key
            ).secret
        ]

        if include_secrets:
            layers = [
                self._layers[
                    layer_id
                ].state_dict()
                for layer_id in self._order
            ]
        else:
            layers = [
                self._layers[
                    layer_id
                ].to_dict(
                    redact_keys=(
                        secret_keys
                    )
                )
                for layer_id in self._order
            ]

        return {
            "format": (
                "SireLLMConfigState"
            ),
            "version": 1,
            "config_version": (
                self.version
            ),
            "schema": schema_state,
            "layers": layers,
        }

    def load_state(
        self,
        state,
    ):
        if not isinstance(
            state,
            dict,
        ):
            raise TypeError(
                "config state must be dict"
            )

        if state.get(
            "format"
        ) != "SireLLMConfigState":
            raise ValueError(
                "invalid config state format"
            )

        if int(
            state.get(
                "version",
                0,
            )
        ) != 1:
            raise ValueError(
                "unsupported config state version"
            )

        staged_schema = (
            ConfigSchema.from_dict(
                state[
                    "schema"
                ]
            )
        )

        staged_layers = {}
        staged_order = []

        for layer_state in state.get(
            "layers",
            [],
        ):
            layer = ConfigLayer.from_dict(
                layer_state
            )

            if layer.layer_id in staged_layers:
                raise ValueError(
                    "duplicate config layer in state"
                )

            staged_schema.validate(
                {
                    key: value
                    for key, value
                    in layer.values.items()
                },
                reject_unknown=True,
            )

            staged_layers[
                layer.layer_id
            ] = layer

            staged_order.append(
                layer.layer_id
            )

        old_schema = self.schema
        old_layers = self._layers
        old_order = self._order
        old_version = self.version

        self.schema = staged_schema
        self._layers = staged_layers
        self._order = staged_order
        self.version = int(
            state.get(
                "config_version",
                0,
            )
        )

        try:
            self._validate_resolved()

        except Exception:
            self.schema = old_schema
            self._layers = old_layers
            self._order = old_order
            self.version = old_version
            raise

        return self

    def status(
        self,
    ):
        resolved = self.resolve_internal()

        secret_count = 0

        for key in self.schema.keys():
            if self.schema.get(
                key
            ).secret:
                secret_count += 1

        return {
            "ready": True,
            "schema_id": (
                self.schema
                .schema_id
            ),
            "config_version": (
                self.version
            ),
            "field_count": len(
                self.schema.keys()
            ),
            "resolved_key_count": len(
                resolved
            ),
            "layer_count": len(
                self._order
            ),
            "secret_field_count": (
                secret_count
            ),
            "layers": self.list_layers(),
        }

    def _validate_partial(
        self,
        values,
    ):
        for key in values:
            if not self.schema.contains(
                key
            ):
                raise ValueError(
                    "unknown config key: "
                    + str(
                        key
                    )
                )

            self.schema.get(
                key
            ).validate(
                values[
                    key
                ]
            )

    def _validate_resolved(
        self,
    ):
        self.schema.validate(
            self._resolve_without_validation(),
            reject_unknown=True,
        )

    def _resolve_without_validation(
        self,
    ):
        result = self.schema.defaults()

        for layer in self._sorted_layers():
            for key in layer.values:
                result[
                    key
                ] = layer._copy(
                    layer.values[
                        key
                    ]
                )

        return result

    def _sorted_layers(
        self,
    ):
        indexed = []

        index = 0

        while index < len(
            self._order
        ):
            layer_id = self._order[
                index
            ]

            layer = self._layers[
                layer_id
            ]

            indexed.append(
                (
                    layer.priority,
                    index,
                    layer,
                )
            )

            index += 1

        indexed.sort(
            key=(
                lambda item: (
                    item[0],
                    item[1],
                )
            )
        )

        return [
            item[2]
            for item in indexed
        ]

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
