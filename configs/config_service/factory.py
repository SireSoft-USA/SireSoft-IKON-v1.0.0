class ConfigServiceConfigFactory:
    """
    Builds the actual layered ConfigManager and ConfigService.
    """

    def build_schema(
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

        schema = ConfigSchema(
            config.schema_id
        )

        for item in config.fields:
            schema.add_field(
                item.to_runtime_field()
            )

        return schema

    def build_manager(
        self,
        config,
        persistence=None,
    ):
        if not isinstance(
            config,
            ConfigServiceConfig,
        ):
            raise TypeError(
                "config must be ConfigServiceConfig"
            )

        ConfigServiceConfigValidator().require_valid(
            config
        )

        if config.load_state_on_start:
            # Start with a placeholder manager; the real schema/layers are
            # restored atomically by ConfigManager.load_state_file().
            manager = ConfigManager(
                persistence=persistence,
            )

            manager.load_state_file(
                config.state_path
            )

            return manager

        manager = ConfigManager(
            schema=self.build_schema(
                config
            ),
            persistence=persistence,
        )

        for layer in config.enabled_layers():
            manager.add_layer(
                layer_id=(
                    layer.layer_id
                ),
                priority=(
                    layer.priority
                ),
                values=(
                    layer.values
                ),
                metadata=(
                    layer.metadata
                ),
            )

        return manager

    def build_service(
        self,
        config,
        persistence=None,
    ):
        return ConfigService(
            self.build_manager(
                config,
                persistence=(
                    persistence
                ),
            )
        )

    def save_state(
        self,
        manager,
        config,
        path_override=None,
    ):
        if not isinstance(
            manager,
            ConfigManager,
        ):
            raise TypeError(
                "manager must be ConfigManager"
            )

        if not isinstance(
            config,
            ConfigServiceConfig,
        ):
            raise TypeError(
                "config must be ConfigServiceConfig"
            )

        path = (
            config.state_path
            if path_override is None
            else path_override
        )

        if path is None:
            raise ValueError(
                "config state path is not configured"
            )

        return manager.save_state(
            path
        )
