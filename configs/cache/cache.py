class CacheConfig:
    def __init__(
        self,
        cache_id,
        max_entries=1024,
        default_ttl_seconds=None,
        enabled=True,
        metadata=None,
    ):
        if not isinstance(cache_id, str) or cache_id == "":
            raise ValueError("cache_id must be non-empty str")

        if not isinstance(max_entries, int) or max_entries <= 0:
            raise ValueError("max_entries must be positive int")

        if default_ttl_seconds is not None and (
            not isinstance(default_ttl_seconds, int)
            or default_ttl_seconds <= 0
        ):
            raise ValueError(
                "default_ttl_seconds must be positive int or None"
            )

        if metadata is None:
            metadata = {}

        if not isinstance(metadata, dict):
            raise TypeError("metadata must be dict or None")

        self.cache_id = cache_id
        self.max_entries = max_entries
        self.default_ttl_seconds = default_ttl_seconds
        self.enabled = bool(enabled)
        self.metadata = self._copy(metadata)

    def to_dict(self):
        return {
            "cache_id": self.cache_id,
            "max_entries": self.max_entries,
            "default_ttl_seconds": self.default_ttl_seconds,
            "enabled": self.enabled,
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
