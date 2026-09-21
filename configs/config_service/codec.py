class ConfigServiceConfigCodec:
    def __init__(
        self,
        parser=None,
    ):
        self.parser = (
            JSONParser()
            if parser is None
            else parser
        )

    def decode_text(
        self,
        text,
    ):
        if not isinstance(
            text,
            str,
        ):
            raise TypeError(
                "config service config text must be str"
            )

        return self.from_dict(
            self.parser.parse(
                text
            )
        )

    def from_dict(
        self,
        value,
    ):
        if not isinstance(
            value,
            dict,
        ):
            raise ValueError(
                "config service config root must be object"
            )

        raw_fields = value.get(
            "fields",
            [],
        )

        raw_layers = value.get(
            "layers",
            [],
        )

        if not isinstance(
            raw_fields,
            list,
        ):
            raise ValueError(
                "fields must be list"
            )

        if not isinstance(
            raw_layers,
            list,
        ):
            raise ValueError(
                "layers must be list"
            )

        fields = []

        for raw in raw_fields:
            if not isinstance(
                raw,
                dict,
            ):
                raise ValueError(
                    "config field definition must be object"
                )

            fields.append(
                RuntimeConfigFieldConfig(
                    key=raw.get(
                        "key"
                    ),
                    value_type=raw.get(
                        "value_type"
                    ),
                    required=raw.get(
                        "required",
                        False,
                    ),
                    default=raw.get(
                        "default"
                    ),
                    secret=raw.get(
                        "secret",
                        False,
                    ),
                    choices=raw.get(
                        "choices"
                    ),
                    minimum=raw.get(
                        "minimum"
                    ),
                    maximum=raw.get(
                        "maximum"
                    ),
                    metadata=raw.get(
                        "metadata",
                        {},
                    ),
                )
            )

        layers = []

        for raw in raw_layers:
            if not isinstance(
                raw,
                dict,
            ):
                raise ValueError(
                    "config layer definition must be object"
                )

            layers.append(
                RuntimeConfigLayerConfig(
                    layer_id=raw.get(
                        "layer_id"
                    ),
                    priority=raw.get(
                        "priority"
                    ),
                    values=raw.get(
                        "values",
                        {},
                    ),
                    metadata=raw.get(
                        "metadata",
                        {},
                    ),
                    enabled=raw.get(
                        "enabled",
                        True,
                    ),
                )
            )

        return ConfigServiceConfig(
            schema_id=value.get(
                "schema_id",
                "sirellm-runtime",
            ),
            fields=fields,
            layers=layers,
            state_path=value.get(
                "state_path"
            ),
            load_state_on_start=(
                value.get(
                    "load_state_on_start",
                    False,
                )
            ),
            metadata=value.get(
                "metadata",
                {},
            ),
        )
