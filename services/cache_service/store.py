class InMemoryCache:
    """
    Named in-memory LRU + TTL cache.

    Eviction priority:
      1. expired entries
      2. least recently accessed entry
      3. deterministic insertion-order tie break
    """

    def __init__(
        self,
        cache_id,
        max_entries=1024,
        default_ttl_seconds=None,
    ):
        if not isinstance(
            cache_id,
            str,
        ) or cache_id == "":
            raise ValueError(
                "cache_id must be non-empty str"
            )

        if (
            not isinstance(
                max_entries,
                int,
            )
            or max_entries <= 0
        ):
            raise ValueError(
                "max_entries must be positive int"
            )

        if default_ttl_seconds is not None:
            if (
                not isinstance(
                    default_ttl_seconds,
                    int,
                )
                or default_ttl_seconds <= 0
            ):
                raise ValueError(
                    "default_ttl_seconds must be positive int or None"
                )

        self.cache_id = cache_id
        self.max_entries = max_entries
        self.default_ttl_seconds = (
            default_ttl_seconds
        )

        self._entries = {}
        self._order = []
        self._access_sequence = 0

        self.hits = 0
        self.misses = 0
        self.sets = 0
        self.deletes = 0
        self.evictions = 0
        self.expirations = 0

    def set(
        self,
        key,
        value,
        now,
        ttl_seconds=None,
        metadata=None,
    ):
        self._validate_now(
            now
        )

        if ttl_seconds is None:
            ttl_seconds = (
                self.default_ttl_seconds
            )

        expires_at = None

        if ttl_seconds is not None:
            if (
                not isinstance(
                    ttl_seconds,
                    int,
                )
                or ttl_seconds <= 0
            ):
                raise ValueError(
                    "ttl_seconds must be positive int or None"
                )

            expires_at = (
                now
                + ttl_seconds
            )

        self.purge_expired(
            now
        )

        existed = key in self._entries

        entry = CacheEntry(
            key=key,
            value=value,
            created_at=now,
            expires_at=expires_at,
            metadata=metadata,
        )

        self._access_sequence += 1
        entry.access_sequence = (
            self._access_sequence
        )

        self._entries[
            key
        ] = entry

        if not existed:
            self._order.append(
                key
            )

        self.sets += 1

        evicted = []

        while len(
            self._entries
        ) > self.max_entries:
            victim = self._lru_key()

            if victim is None:
                break

            self._remove(
                victim,
                reason="eviction",
            )

            evicted.append(
                victim
            )

        return {
            "entry": (
                entry.to_dict()
            ),
            "replaced": existed,
            "evicted_keys": evicted,
        }

    def get(
        self,
        key,
        now,
        default=None,
    ):
        self._validate_now(
            now
        )

        if key not in self._entries:
            self.misses += 1

            return {
                "found": False,
                "key": key,
                "value": self._copy(
                    default
                ),
                "entry": None,
            }

        entry = self._entries[
            key
        ]

        if entry.expired(
            now
        ):
            self._remove(
                key,
                reason="expiration",
            )

            self.misses += 1

            return {
                "found": False,
                "key": key,
                "value": self._copy(
                    default
                ),
                "entry": None,
            }

        self._access_sequence += 1

        entry.touch(
            now,
            self._access_sequence,
        )

        self.hits += 1

        return {
            "found": True,
            "key": key,
            "value": self._copy(
                entry.value
            ),
            "entry": (
                entry.to_dict(
                    include_value=False
                )
            ),
        }

    def peek(
        self,
        key,
        now,
        default=None,
    ):
        self._validate_now(
            now
        )

        if key not in self._entries:
            return {
                "found": False,
                "key": key,
                "value": self._copy(
                    default
                ),
                "entry": None,
            }

        entry = self._entries[
            key
        ]

        if entry.expired(
            now
        ):
            self._remove(
                key,
                reason="expiration",
            )

            return {
                "found": False,
                "key": key,
                "value": self._copy(
                    default
                ),
                "entry": None,
            }

        return {
            "found": True,
            "key": key,
            "value": self._copy(
                entry.value
            ),
            "entry": (
                entry.to_dict(
                    include_value=False
                )
            ),
        }

    def contains(
        self,
        key,
        now,
    ):
        return self.peek(
            key,
            now,
        )[
            "found"
        ]

    def delete(
        self,
        key,
    ):
        if key not in self._entries:
            return {
                "deleted": False,
                "key": key,
            }

        self._remove(
            key,
            reason="delete",
        )

        return {
            "deleted": True,
            "key": key,
        }

    def clear(
        self,
    ):
        count = len(
            self._entries
        )

        self._entries = {}
        self._order = []

        return {
            "cleared_entries": count,
        }

    def purge_expired(
        self,
        now,
    ):
        self._validate_now(
            now
        )

        expired = []

        for key in list(
            self._order
        ):
            if key not in self._entries:
                continue

            if self._entries[
                key
            ].expired(
                now
            ):
                self._remove(
                    key,
                    reason="expiration",
                )

                expired.append(
                    key
                )

        return {
            "expired_keys": expired,
            "expired_count": len(
                expired
            ),
        }

    def keys(
        self,
        now=None,
    ):
        if now is not None:
            self.purge_expired(
                now
            )

        return [
            key
            for key in self._order
            if key in self._entries
        ]

    def count(
        self,
        now=None,
    ):
        if now is not None:
            self.purge_expired(
                now
            )

        return len(
            self._entries
        )

    def stats(
        self,
        now=None,
    ):
        if now is not None:
            self.purge_expired(
                now
            )

        total_reads = (
            self.hits
            + self.misses
        )

        hit_rate = 0.0

        if total_reads > 0:
            hit_rate = (
                self.hits
                / total_reads
            )

        return {
            "cache_id": (
                self.cache_id
            ),
            "max_entries": (
                self.max_entries
            ),
            "default_ttl_seconds": (
                self.default_ttl_seconds
            ),
            "entries": len(
                self._entries
            ),
            "hits": self.hits,
            "misses": self.misses,
            "hit_rate": hit_rate,
            "sets": self.sets,
            "deletes": self.deletes,
            "evictions": (
                self.evictions
            ),
            "expirations": (
                self.expirations
            ),
            "access_sequence": (
                self._access_sequence
            ),
        }

    def export_state(
        self,
    ):
        return {
            "cache_id": (
                self.cache_id
            ),
            "max_entries": (
                self.max_entries
            ),
            "default_ttl_seconds": (
                self.default_ttl_seconds
            ),
            "entries": [
                self._entries[
                    key
                ].to_dict()
                for key in self._order
                if key in self._entries
            ],
            "stats": {
                "hits": self.hits,
                "misses": (
                    self.misses
                ),
                "sets": self.sets,
                "deletes": (
                    self.deletes
                ),
                "evictions": (
                    self.evictions
                ),
                "expirations": (
                    self.expirations
                ),
                "access_sequence": (
                    self._access_sequence
                ),
            },
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
                "cache state must be dict"
            )

        if state[
            "cache_id"
        ] != self.cache_id:
            raise ValueError(
                "cache identity mismatch"
            )

        max_entries = int(
            state[
                "max_entries"
            ]
        )

        default_ttl = state.get(
            "default_ttl_seconds"
        )

        if max_entries <= 0:
            raise ValueError(
                "cache state max_entries must be positive"
            )

        if default_ttl is not None:
            default_ttl = int(
                default_ttl
            )

            if default_ttl <= 0:
                raise ValueError(
                    "cache state TTL must be positive"
                )

        staged_entries = {}
        staged_order = []

        for row in state.get(
            "entries",
            [],
        ):
            entry = CacheEntry.from_dict(
                row
            )

            if entry.key in staged_entries:
                raise ValueError(
                    "duplicate cache entry key in state"
                )

            staged_entries[
                entry.key
            ] = entry

            staged_order.append(
                entry.key
            )

        if len(
            staged_entries
        ) > max_entries:
            raise ValueError(
                "cache state exceeds configured capacity"
            )

        stats = state.get(
            "stats",
            {},
        )

        self.max_entries = (
            max_entries
        )
        self.default_ttl_seconds = (
            default_ttl
        )
        self._entries = (
            staged_entries
        )
        self._order = (
            staged_order
        )

        self.hits = int(
            stats.get(
                "hits",
                0,
            )
        )
        self.misses = int(
            stats.get(
                "misses",
                0,
            )
        )
        self.sets = int(
            stats.get(
                "sets",
                0,
            )
        )
        self.deletes = int(
            stats.get(
                "deletes",
                0,
            )
        )
        self.evictions = int(
            stats.get(
                "evictions",
                0,
            )
        )
        self.expirations = int(
            stats.get(
                "expirations",
                0,
            )
        )
        self._access_sequence = int(
            stats.get(
                "access_sequence",
                0,
            )
        )

        return self

    def _lru_key(
        self,
    ):
        victim = None
        best_sequence = None
        best_order = None

        index = 0

        while index < len(
            self._order
        ):
            key = self._order[
                index
            ]

            if key in self._entries:
                sequence = (
                    self._entries[
                        key
                    ].access_sequence
                )

                if (
                    victim is None
                    or sequence
                    < best_sequence
                    or (
                        sequence
                        == best_sequence
                        and index
                        < best_order
                    )
                ):
                    victim = key
                    best_sequence = (
                        sequence
                    )
                    best_order = index

            index += 1

        return victim

    def _remove(
        self,
        key,
        reason,
    ):
        if key not in self._entries:
            return

        del self._entries[
            key
        ]

        self._order = [
            existing
            for existing in self._order
            if existing != key
        ]

        if reason == "delete":
            self.deletes += 1

        elif reason == "eviction":
            self.evictions += 1

        elif reason == "expiration":
            self.expirations += 1

    def _validate_now(
        self,
        now,
    ):
        if not isinstance(
            now,
            int,
        ):
            raise TypeError(
                "now must be integer seconds"
            )

        if now < 0:
            raise ValueError(
                "now must be non-negative"
            )

    def _copy(
        self,
        value,
    ):
        if isinstance(
            value,
            dict,
        ):
            result = {}

            for key in value:
                result[
                    key
                ] = self._copy(
                    value[
                        key
                    ]
                )

            return result

        if isinstance(
            value,
            list,
        ):
            return [
                self._copy(
                    item
                )
                for item in value
            ]

        if isinstance(
            value,
            tuple,
        ):
            return [
                self._copy(
                    item
                )
                for item in value
            ]

        return value
