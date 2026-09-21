class StoragePathPolicy:
    """
    Deterministic, traversal-safe namespace/key path policy.
    """

    def __init__(
        self,
        root_path,
        extension=".sllmdata",
    ):
        if not isinstance(root_path, str) or root_path == "":
            raise ValueError(
                "root_path must be non-empty str"
            )

        if not isinstance(extension, str) or extension == "":
            raise ValueError(
                "extension must be non-empty str"
            )

        if not extension.startswith("."):
            raise ValueError(
                "extension must start with '.'"
            )

        self.root_path = root_path.rstrip(
            "/\\"
        )
        self.extension = extension

    def namespace_path(
        self,
        namespace,
    ):
        return (
            self.root_path
            + "/"
            + self._segment(
                namespace,
                "namespace",
            )
        )

    def key_path(
        self,
        namespace,
        key,
    ):
        return (
            self.namespace_path(
                namespace
            )
            + "/"
            + self._segment(
                key,
                "key",
            )
            + self.extension
        )

    def temporary_path(
        self,
        namespace,
        key,
    ):
        return (
            self.key_path(
                namespace,
                key,
            )
            + ".tmp"
        )

    def _segment(
        self,
        value,
        field_name,
    ):
        if not isinstance(value, str) or value == "":
            raise ValueError(
                field_name
                + " must be non-empty str"
            )

        if (
            value in (".", "..")
            or "/" in value
            or "\\" in value
            or "\x00" in value
            or ".." in value
        ):
            raise ValueError(
                field_name
                + " contains unsafe path characters"
            )

        return value
