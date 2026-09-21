class ConfigServiceConfig:
    def __init__(
        self,
        schema_id="sirellm-runtime",
        fields=None,
        layers=None,
        state_path=None,
        load_state_on_start=False,
        metadata=None,
    ):
        if (
            not isinstance(
                schema_id,
                str,
            )
            or schema_id == ""
        ):
            raise ValueError(
                "schema_id must be non-empty str"
            )

        if fields is None:
            fields = []

        if layers is None:
            layers = []

        if not isinstance(
            fields,
            (list, tuple),
        ):
            raise TypeError(
                "fields must be list/tuple or None"
            )

        if not isinstance(
            layers,
            (list, tuple),
        ):
            raise TypeError(
                "layers must be list/tuple or None"
            )

        normalized_fields = []
        field_keys = {}

        for field in fields:
            if not isinstance(
                field,
                RuntimeConfigFieldConfig,
            ):
                raise TypeError(
                    "field entries must be RuntimeConfigFieldConfig"
                )

            if field.key in field_keys:
                raise ValueError(
                    "duplicate config field: "
                    + field.key
                )

            field_keys[
                field.key
            ] = True
            normalized_fields.append(
                field
            )

        normalized_layers = []
        layer_ids = {}

        for layer in layers:
            if not isinstance(
                layer,
                RuntimeConfigLayerConfig,
            ):
                raise TypeError(
                    "layer entries must be RuntimeConfigLayerConfig"
                )

            if layer.layer_id in layer_ids:
                raise ValueError(
                    "duplicate config layer: "
                    + layer.layer_id
                )

            layer_ids[
                layer.layer_id
            ] = True
            normalized_layers.append(
                layer
            )

        if state_path is not None and (
            not isinstance(
                state_path,
                str,
            )
            or state_path == ""
        ):
            raise ValueError(
                "state_path must be non-empty str or None"
            )

        if (
            load_state_on_start
            and state_path is None
        ):
            raise ValueError(
                "load_state_on_start requires state_path"
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

        self.schema_id = schema_id
        self.fields = normalized_fields
        self.layers = normalized_layers
        self.state_path = state_path
        self.load_state_on_start = bool(
            load_state_on_start
        )
        self.metadata = self._copy(
            metadata
        )

    def enabled_layers(
        self,
    ):
        return [
            layer
            for layer
            in self.layers
            if layer.enabled
        ]

    def to_dict(
        self,
    ):
        return {
            "schema_id": (
                self.schema_id
            ),
            "fields": [
                field.to_dict()
                for field
                in self.fields
            ],
            "layers": [
                layer.to_dict()
                for layer
                in self.layers
            ],
            "state_path": (
                self.state_path
            ),
            "load_state_on_start": (
                self.load_state_on_start
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
