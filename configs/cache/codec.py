class CacheConfigCodec:
    def __init__(self, parser=None):
        self.parser = (
            JSONParser()
            if parser is None
            else parser
        )

    def decode_text(self, text):
        if not isinstance(text, str):
            raise TypeError(
                "cache config text must be str"
            )

        return self.from_dict(
            self.parser.parse(text)
        )

    def from_dict(self, value):
        if not isinstance(value, dict):
            raise ValueError(
                "cache config root must be object"
            )

        raw_caches = value.get("caches")

        if not isinstance(raw_caches, list) or len(raw_caches) == 0:
            raise ValueError(
                "caches must be non-empty list"
            )

        caches = []

        for raw in raw_caches:
            if not isinstance(raw, dict):
                raise ValueError(
                    "cache entry must be object"
                )

            caches.append(
                CacheConfig(
                    cache_id=raw.get("cache_id"),
                    max_entries=raw.get(
                        "max_entries",
                        1024,
                    ),
                    default_ttl_seconds=raw.get(
                        "default_ttl_seconds"
                    ),
                    enabled=raw.get(
                        "enabled",
                        True,
                    ),
                    metadata=raw.get(
                        "metadata",
                        {},
                    ),
                )
            )

        return CacheServiceConfig(
            caches=caches,
            persistence_path=value.get(
                "persistence_path"
            ),
            metadata=value.get(
                "metadata",
                {},
            ),
        )
