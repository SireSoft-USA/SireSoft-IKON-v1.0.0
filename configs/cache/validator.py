class CacheConfigValidator:
    def validate(self, config):
        if not isinstance(config, CacheServiceConfig):
            raise TypeError(
                "config must be CacheServiceConfig"
            )

        errors = []
        warnings = []

        enabled = config.enabled_caches()

        if len(enabled) == 0:
            warnings.append({
                "code": "NO_ENABLED_CACHES",
                "message": "No caches are enabled",
            })

        total_capacity = 0

        for cache in config.caches:
            total_capacity += cache.max_entries

            if cache.default_ttl_seconds is None:
                warnings.append({
                    "code": "CACHE_WITHOUT_DEFAULT_TTL",
                    "cache_id": cache.cache_id,
                    "message": "Cache has no default TTL",
                })

            if cache.max_entries > 1000000:
                warnings.append({
                    "code": "VERY_LARGE_CACHE",
                    "cache_id": cache.cache_id,
                    "message": "Cache max_entries is unusually large",
                })

        if total_capacity > 5000000:
            warnings.append({
                "code": "VERY_LARGE_TOTAL_CACHE_CAPACITY",
                "message": "Total configured cache capacity is unusually large",
            })

        return {
            "valid": len(errors) == 0,
            "error_count": len(errors),
            "warning_count": len(warnings),
            "errors": errors,
            "warnings": warnings,
            "enabled_cache_count": len(enabled),
            "total_capacity": total_capacity,
        }

    def require_valid(self, config):
        result = self.validate(config)

        if not result["valid"]:
            first = result["errors"][0]

            raise ValueError(
                first["code"]
                + ": "
                + first["message"]
            )

        return result
