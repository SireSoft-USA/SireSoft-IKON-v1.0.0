class LoggingConfigFactory:
    """
    Builds the runtime LoggingManager from validated serializable config.
    """

    def build_manager(
        self,
        config,
        sanitizer=None,
        archive=None,
    ):
        if not isinstance(
            config,
            LoggingConfig,
        ):
            raise TypeError(
                "config must be LoggingConfig"
            )

        LoggingConfigValidator().require_valid(
            config
        )

        sink = config.enabled_sinks()[
            0
        ]

        return LoggingManager(
            minimum_level=(
                config.minimum_level
            ),
            max_records=(
                sink.max_records
            ),
            sanitizer=sanitizer,
            archive=archive,
        )

    def archive_path(
        self,
        config,
    ):
        if not isinstance(
            config,
            LoggingConfig,
        ):
            raise TypeError(
                "config must be LoggingConfig"
            )

        return config.archive_path
