class CheckpointPathPolicy:
    """
    Safe deterministic path policy for model/version checkpoint artifacts.
    """

    def __init__(
        self,
        root_path,
        extension=".sllmckpt",
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

    def artifact_path(
        self,
        model_id,
        version,
    ):
        model_segment = self._segment(
            model_id,
            "model_id",
        )

        version_segment = self._segment(
            version,
            "version",
        )

        return (
            self.root_path
            + "/"
            + model_segment
            + "/"
            + version_segment
            + self.extension
        )

    def model_directory(
        self,
        model_id,
    ):
        return (
            self.root_path
            + "/"
            + self._segment(
                model_id,
                "model_id",
            )
        )

    def _segment(
        self,
        value,
        field_name,
    ):
        if not isinstance(value, str) or value == "":
            raise ValueError(
                field_name + " must be non-empty str"
            )

        if value in (
            ".",
            "..",
        ):
            raise ValueError(
                field_name + " contains unsafe path segment"
            )

        if (
            "/"
            in value
            or "\\"
            in value
            or "\x00"
            in value
        ):
            raise ValueError(
                field_name + " contains unsafe path characters"
            )

        if ".." in value:
            raise ValueError(
                field_name + " contains traversal sequence"
            )

        return value
