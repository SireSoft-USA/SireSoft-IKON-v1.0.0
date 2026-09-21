class DatasetSourceConfig:
    """
    Serializable declaration of an immutable raw dataset source.
    """

    FORMATS = (
        "json",
        "jsonl",
        "text",
        "gzip",
    )

    def __init__(
        self,
        path,
        source_format,
        role="data",
        required=True,
        metadata=None,
    ):
        if not isinstance(
            path,
            str,
        ) or path == "":
            raise ValueError(
                "path must be non-empty str"
            )

        if source_format not in self.FORMATS:
            raise ValueError(
                "unsupported dataset source format"
            )

        if not isinstance(
            role,
            str,
        ) or role == "":
            raise ValueError(
                "role must be non-empty str"
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

        self.path = path
        self.source_format = (
            source_format
        )
        self.role = role
        self.required = bool(
            required
        )
        self.metadata = self._copy(
            metadata
        )

    def to_dict(
        self,
    ):
        return {
            "path": self.path,
            "format": (
                self.source_format
            ),
            "role": self.role,
            "required": (
                self.required
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
                    value[key]
                )
                for key
                in value
            }

        if isinstance(
            value,
            (list, tuple),
        ):
            return [
                self._copy(item)
                for item
                in value
            ]

        return value
