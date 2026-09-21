class SireSoftVectorPathPolicy:
    """
    Safe path policy for versioned SireSoft retrieval snapshots.
    """

    def __init__(
        self,
        root_path,
        extension=".slretr",
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

    def snapshot_path(
        self,
        version,
    ):
        return (
            self.root_path
            + "/"
            + self._segment(
                version
            )
            + self.extension
        )

    def _segment(
        self,
        value,
    ):
        if not isinstance(
            value,
            str,
        ) or value == "":
            raise ValueError(
                "version must be non-empty str"
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
                "version contains unsafe path characters"
            )

        return value
