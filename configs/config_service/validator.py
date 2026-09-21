class ConfigServiceConfigValidator:
    def validate(
        self,
        config,
    ):
        if not isinstance(
            config,
            ConfigServiceConfig,
        ):
            raise TypeError(
                "config must be ConfigServiceConfig"
            )

        errors = []
        warnings = []

        field_map = {
            field.key: field
            for field
            in config.fields
        }

        for layer in (
            config.enabled_layers()
        ):
            for key in layer.values:
                if key not in field_map:
                    errors.append({
                        "code": (
                            "UNKNOWN_CONFIG_LAYER_KEY"
                        ),
                        "layer_id": (
                            layer.layer_id
                        ),
                        "key": key,
                        "message": (
                            "Layer contains a key not declared by the schema"
                        ),
                    })
                    continue

                try:
                    field_map[
                        key
                    ].to_runtime_field().validate(
                        layer.values[
                            key
                        ]
                    )

                except Exception as error:
                    errors.append({
                        "code": (
                            "INVALID_CONFIG_LAYER_VALUE"
                        ),
                        "layer_id": (
                            layer.layer_id
                        ),
                        "key": key,
                        "message": str(
                            error
                        ),
                    })

        if len(
            config.fields
        ) == 0 and not config.load_state_on_start:
            warnings.append({
                "code": (
                    "EMPTY_RUNTIME_CONFIG_SCHEMA"
                ),
                "message": (
                    "Runtime config schema contains no fields"
                ),
            })

        if (
            config.state_path
            is not None
            and not config
            .load_state_on_start
        ):
            warnings.append({
                "code": (
                    "CONFIG_STATE_NOT_AUTO_LOADED"
                ),
                "message": (
                    "state_path is configured but startup load is disabled"
                ),
            })

        return {
            "valid": (
                len(
                    errors
                )
                == 0
            ),
            "error_count": len(
                errors
            ),
            "warning_count": len(
                warnings
            ),
            "errors": errors,
            "warnings": warnings,
            "field_count": len(
                config.fields
            ),
            "enabled_layer_count": len(
                config.enabled_layers()
            ),
        }

    def require_valid(
        self,
        config,
    ):
        result = self.validate(
            config
        )

        if not result[
            "valid"
        ]:
            first = result[
                "errors"
            ][0]

            raise ValueError(
                first[
                    "code"
                ]
                + ": "
                + first[
                    "message"
                ]
            )

        return result
