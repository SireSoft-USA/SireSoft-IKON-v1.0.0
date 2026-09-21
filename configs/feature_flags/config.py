class FeatureFlagsConfig:
    def __init__(
        self,
        flags,
        persistence_path=None,
        publish_events=False,
        metadata=None,
    ):
        if not isinstance(
            flags,
            (list, tuple),
        ) or len(
            flags
        ) == 0:
            raise ValueError(
                "flags must be non-empty list/tuple"
            )

        normalized = []
        seen = {}

        for flag in flags:
            if not isinstance(
                flag,
                FeatureFlagConfig,
            ):
                raise TypeError(
                    "flags entries must be FeatureFlagConfig"
                )

            if flag.flag_key in seen:
                raise ValueError(
                    "duplicate flag_key: "
                    + flag.flag_key
                )

            seen[
                flag.flag_key
            ] = True

            normalized.append(
                flag
            )

        if persistence_path is not None and (
            not isinstance(
                persistence_path,
                str,
            )
            or persistence_path == ""
        ):
            raise ValueError(
                "persistence_path must be non-empty str or None"
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

        self.flags = normalized
        self.persistence_path = (
            persistence_path
        )
        self.publish_events = bool(
            publish_events
        )
        self.metadata = self._copy(
            metadata
        )

    def flag_map(
        self,
    ):
        return {
            flag.flag_key: flag
            for flag
            in self.flags
        }

    def to_dict(
        self,
    ):
        return {
            "flags": [
                flag.to_dict()
                for flag
                in self.flags
            ],
            "persistence_path": (
                self.persistence_path
            ),
            "publish_events": (
                self.publish_events
            ),
            "metadata": self._copy(
                self.metadata
            ),
        }

    def _copy(
        self,
        value,
    ):
        if isinstance(
            value,
            dict,
        ):
            return {
                key: self._copy(
                    value[
                        key
                    ]
                )
                for key
                in value
            }

        if isinstance(
            value,
            (list, tuple),
        ):
            return [
                self._copy(
                    item
                )
                for item
                in value
            ]

        return value
