class CacheConfigFactory:
    def build_manager(
        self,
        config,
        persistence=None,
    ):
        if not isinstance(config, CacheServiceConfig):
            raise TypeError(
                "config must be CacheServiceConfig"
            )

        manager = CacheManager(
            persistence=persistence
        )

        for cache in config.enabled_caches():
            manager.create_cache(
                cache_id=cache.cache_id,
                max_entries=cache.max_entries,
                default_ttl_seconds=(
                    cache.default_ttl_seconds
                ),
            )

        return manager

    def initialize(
        self,
        config,
        manager=None,
        load_persisted=False,
    ):
        if not isinstance(config, CacheServiceConfig):
            raise TypeError(
                "config must be CacheServiceConfig"
            )

        if manager is None:
            manager = self.build_manager(
                config
            )

        if not isinstance(manager, CacheManager):
            raise TypeError(
                "manager must be CacheManager or None"
            )

        if (
            load_persisted
            and config.persistence_path is not None
        ):
            manager.load_state_file(
                config.persistence_path
            )

        return manager
