class StorageNamespace:
    """
    Metadata-only namespace descriptor.
    """

    def __init__(
        self,
        name,
        description="",
        metadata=None,
    ):
        if not isinstance(name, str) or name == "":
            raise ValueError(
                "name must be non-empty str"
            )

        if not isinstance(description, str):
            raise TypeError(
                "description must be str"
            )

        if metadata is None:
            metadata = {}

        if not isinstance(metadata, dict):
            raise TypeError(
                "metadata must be dict or None"
            )

        self.name = name
        self.description = description
        self.metadata = self._copy(
            metadata
        )

    def to_dict(
        self,
    ):
        return {
            "name": self.name,
            "description": (
                self.description
            ),
            "metadata": self._copy(
                self.metadata
            ),
        }

    def _copy(
        self,
        value,
    ):
        if isinstance(value, dict):
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

        if isinstance(value, list):
            return [
                self._copy(
                    item
                )
                for item in value
            ]

        if isinstance(value, tuple):
            return [
                self._copy(
                    item
                )
                for item in value
            ]

        return value
