class CacheServiceConfig:
    def __init__(
        self,
        caches,
        persistence_path=None,
        metadata=None,
    ):
        if not isinstance(caches, (list, tuple)) or len(caches) == 0:
            raise ValueError(
                "caches must be non-empty list/tuple"
            )

        normalized = []
        seen = {}

        for cache in caches:
            if not isinstance(cache, CacheConfig):
                raise TypeError(
                    "caches entries must be CacheConfig"
                )

            if cache.cache_id in seen:
                raise ValueError(
                    "duplicate cache_id: " + cache.cache_id
                )

            seen[cache.cache_id] = True
            normalized.append(cache)

        if persistence_path is not None and (
            not isinstance(persistence_path, str)
            or persistence_path == ""
        ):
            raise ValueError(
                "persistence_path must be non-empty str or None"
            )

        if metadata is None:
            metadata = {}

        if not isinstance(metadata, dict):
            raise TypeError("metadata must be dict or None")

        self.caches = normalized
        self.persistence_path = persistence_path
        self.metadata = self._copy(metadata)

    def cache_map(self):
        return {
            cache.cache_id: cache
            for cache in self.caches
        }

    def enabled_caches(self):
        return [
            cache
            for cache in self.caches
            if cache.enabled
        ]

    def to_dict(self):
        return {
            "caches": [
                cache.to_dict()
                for cache in self.caches
            ],
            "persistence_path": self.persistence_path,
            "metadata": self._copy(self.metadata),
        }

    def _copy(self, value):
        if isinstance(value, dict):
            return {
                key: self._copy(value[key])
                for key in value
            }

        if isinstance(value, (list, tuple)):
            return [
                self._copy(item)
                for item in value
            ]

        return value
