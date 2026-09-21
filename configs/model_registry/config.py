class ModelRegistryConfig:
    """
    Startup configuration for the versioned model registry.
    """

    def __init__(
        self,
        versions,
        verify_all=False,
        fail_on_verification_error=True,
        metadata=None,
    ):
        if not isinstance(
            versions,
            (list, tuple),
        ) or len(
            versions
        ) == 0:
            raise ValueError(
                "versions must be non-empty list/tuple"
            )

        normalized = []
        seen = {}

        for item in versions:
            if not isinstance(
                item,
                ModelVersionConfig,
            ):
                raise TypeError(
                    "versions entries must be ModelVersionConfig"
                )

            key = item.key()

            if key in seen:
                raise ValueError(
                    "duplicate model version config: "
                    + key
                )

            seen[
                key
            ] = True
            normalized.append(
                item
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

        self.versions = normalized
        self.verify_all = bool(
            verify_all
        )
        self.fail_on_verification_error = bool(
            fail_on_verification_error
        )
        self.metadata = self._copy(
            metadata
        )

    def enabled_versions(
        self,
    ):
        return [
            item
            for item
            in self.versions
            if item.enabled
        ]

    def to_dict(
        self,
    ):
        return {
            "versions": [
                item.to_dict()
                for item
                in self.versions
            ],
            "verify_all": (
                self.verify_all
            ),
            "fail_on_verification_error": (
                self.fail_on_verification_error
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
