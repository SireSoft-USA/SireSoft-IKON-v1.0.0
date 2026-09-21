class VectorIndexPathPolicy:
    """
    Safe deterministic index/version artifact path policy.
    """

    def __init__(
        self,
        root_path,
        extension=".sllmvidx",
    ):
        if not isinstance(
            root_path,
            str,
        ) or root_path == "":
            raise ValueError(
                "root_path must be non-empty str"
            )

        if not isinstance(
            extension,
            str,
        ) or extension == "":
            raise ValueError(
                "extension must be non-empty str"
            )

        if not extension.startswith(
            "."
        ):
            raise ValueError(
                "extension must start with '.'"
            )

        self.root_path = (
            root_path.rstrip(
                "/\\"
            )
        )
        self.extension = extension

    def index_directory(
        self,
        index_id,
    ):
        return (
            self.root_path
            + "/"
            + self._segment(
                index_id,
                "index_id",
            )
        )

    def artifact_path(
        self,
        index_id,
        version,
    ):
        return (
            self.index_directory(
                index_id
            )
            + "/"
            + self._segment(
                version,
                "version",
            )
            + self.extension
        )

    def _segment(
        self,
        value,
        field_name,
    ):
        if not isinstance(
            value,
            str,
        ) or value == "":
            raise ValueError(
                field_name
                + " must be non-empty str"
            )

        if (
            value in (
                ".",
                "..",
            )
            or "/"
            in value
            or "\\"
            in value
            or "\x00"
            in value
            or ".."
            in value
        ):
            raise ValueError(
                field_name
                + " contains unsafe path characters"
            )

        return value
