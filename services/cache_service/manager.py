class CacheManager:
    """
    Owns independent named caches and their persistence lifecycle.
    """

    def __init__(
        self,
        persistence=None,
    ):
        self.persistence = (
            CachePersistence()
            if persistence is None
            else persistence
        )

        self._caches = {}
        self._order = []

    def create_cache(
        self,
        cache_id,
        max_entries=1024,
        default_ttl_seconds=None,
    ):
        if cache_id in self._caches:
            raise ValueError(
                "cache already exists: "
                + str(
                    cache_id
                )
            )

        cache = InMemoryCache(
            cache_id=cache_id,
            max_entries=max_entries,
            default_ttl_seconds=(
                default_ttl_seconds
            ),
        )

        self._caches[
            cache_id
        ] = cache

        self._order.append(
            cache_id
        )

        return cache

    def remove_cache(
        self,
        cache_id,
    ):
        cache = self.get_cache(
            cache_id
        )

        del self._caches[
            cache_id
        ]

        self._order = [
            existing
            for existing in self._order
            if existing != cache_id
        ]

        return cache

    def get_cache(
        self,
        cache_id,
    ):
        if cache_id not in self._caches:
            raise KeyError(
                "cache not found: "
                + str(
                    cache_id
                )
            )

        return self._caches[
            cache_id
        ]

    def list_caches(
        self,
        now=None,
    ):
        return [
            self._caches[
                cache_id
            ].stats(
                now=now
            )
            for cache_id in self._order
        ]

    def set(
        self,
        cache_id,
        key,
        value,
        now,
        ttl_seconds=None,
        metadata=None,
    ):
        return self.get_cache(
            cache_id
        ).set(
            key=key,
            value=value,
            now=now,
            ttl_seconds=(
                ttl_seconds
            ),
            metadata=metadata,
        )

    def get(
        self,
        cache_id,
        key,
        now,
        default=None,
    ):
        return self.get_cache(
            cache_id
        ).get(
            key=key,
            now=now,
            default=default,
        )

    def peek(
        self,
        cache_id,
        key,
        now,
        default=None,
    ):
        return self.get_cache(
            cache_id
        ).peek(
            key=key,
            now=now,
            default=default,
        )

    def delete(
        self,
        cache_id,
        key,
    ):
        return self.get_cache(
            cache_id
        ).delete(
            key
        )

    def clear(
        self,
        cache_id,
    ):
        return self.get_cache(
            cache_id
        ).clear()

    def purge_expired(
        self,
        cache_id,
        now,
    ):
        return self.get_cache(
            cache_id
        ).purge_expired(
            now
        )

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
    ):
        return {
            "format": (
                "SireLLMCacheState"
            ),
            "version": 1,
            "caches": [
                self._caches[
                    cache_id
                ].export_state()
                for cache_id in self._order
            ],
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
                "cache manager state must be dict"
            )

        if state.get(
            "format"
        ) != "SireLLMCacheState":
            raise ValueError(
                "invalid cache manager state format"
            )

        if int(
            state.get(
                "version",
                0,
            )
        ) != 1:
            raise ValueError(
                "unsupported cache manager state version"
            )

        staged = {}
        order = []

        for cache_state in state.get(
            "caches",
            [],
        ):
            cache_id = cache_state[
                "cache_id"
            ]

            if cache_id in staged:
                raise ValueError(
                    "duplicate cache in manager state"
                )

            cache = InMemoryCache(
                cache_id=cache_id,
                max_entries=int(
                    cache_state[
                        "max_entries"
                    ]
                ),
                default_ttl_seconds=(
                    cache_state.get(
                        "default_ttl_seconds"
                    )
                ),
            )

            cache.load_state(
                cache_state
            )

            staged[
                cache_id
            ] = cache

            order.append(
                cache_id
            )

        self._caches = staged
        self._order = order

        return self

    def status(
        self,
        now=None,
    ):
        caches = self.list_caches(
            now=now
        )

        total_entries = 0
        total_hits = 0
        total_misses = 0
        total_evictions = 0
        total_expirations = 0

        for item in caches:
            total_entries += item[
                "entries"
            ]
            total_hits += item[
                "hits"
            ]
            total_misses += item[
                "misses"
            ]
            total_evictions += item[
                "evictions"
            ]
            total_expirations += item[
                "expirations"
            ]

        return {
            "ready": True,
            "cache_count": len(
                caches
            ),
            "total_entries": (
                total_entries
            ),
            "total_hits": (
                total_hits
            ),
            "total_misses": (
                total_misses
            ),
            "total_evictions": (
                total_evictions
            ),
            "total_expirations": (
                total_expirations
            ),
            "eviction_policy": "lru",
            "caches": caches,
        }
