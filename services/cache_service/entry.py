class CacheEntry:
    """
    One deterministic cache entry.

    Time is supplied explicitly by callers. No hidden wall-clock dependency is
    used in the cache core.
    """

    def __init__(
        self,
        key,
        value,
        created_at,
        expires_at=None,
        metadata=None,
    ):
        if not isinstance(
            key,
            str,
        ) or key == "":
            raise ValueError(
                "cache key must be non-empty str"
            )

        if not isinstance(
            created_at,
            int,
        ) or created_at < 0:
            raise ValueError(
                "created_at must be non-negative int"
            )

        if expires_at is not None:
            if (
                not isinstance(
                    expires_at,
                    int,
                )
                or expires_at <= created_at
            ):
                raise ValueError(
                    "expires_at must be int greater than created_at or None"
                )

        if metadata is None:
            metadata = {}

        if not isinstance(
            metadata,
            dict,
        ):
            raise TypeError(
                "metadata must be dict or None"
            )

        self.key = key
        self.value = self._copy(
            value
        )
        self.created_at = created_at
        self.expires_at = expires_at
        self.metadata = self._copy(
            metadata
        )

        self.hits = 0
        self.last_access = created_at
        self.access_sequence = 0

    def expired(
        self,
        now,
    ):
        if not isinstance(
            now,
            int,
        ) or now < 0:
            raise ValueError(
                "now must be non-negative int"
            )

        return (
            self.expires_at
            is not None
            and now
            >= self.expires_at
        )

    def touch(
        self,
        now,
        access_sequence,
    ):
        if not isinstance(
            now,
            int,
        ) or now < 0:
            raise ValueError(
                "now must be non-negative int"
            )

        self.hits += 1
        self.last_access = now
        self.access_sequence = int(
            access_sequence
        )

    def to_dict(
        self,
        include_value=True,
    ):
        result = {
            "key": self.key,
            "created_at": self.created_at,
            "expires_at": self.expires_at,
            "metadata": self._copy(
                self.metadata
            ),
            "hits": self.hits,
            "last_access": self.last_access,
            "access_sequence": (
                self.access_sequence
            ),
        }

        if include_value:
            result[
                "value"
            ] = self._copy(
                self.value
            )

        return result

    @classmethod
    def from_dict(
        cls,
        state,
    ):
        if not isinstance(
            state,
            dict,
        ):
            raise TypeError(
                "cache entry state must be dict"
            )

        entry = cls(
            key=state[
                "key"
            ],
            value=state.get(
                "value"
            ),
            created_at=int(
                state[
                    "created_at"
                ]
            ),
            expires_at=state.get(
                "expires_at"
            ),
            metadata=state.get(
                "metadata",
                {},
            ),
        )

        entry.hits = int(
            state.get(
                "hits",
                0,
            )
        )

        entry.last_access = int(
            state.get(
                "last_access",
                entry.created_at,
            )
        )

        entry.access_sequence = int(
            state.get(
                "access_sequence",
                0,
            )
        )

        return entry

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
