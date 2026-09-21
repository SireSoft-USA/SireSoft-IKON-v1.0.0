import os


class RuntimeProfileLoader:
    """
    Filesystem loader restricted to a configured profile root.
    """

    def __init__(
        self,
        root,
        codec=None,
    ):
        if not isinstance(
            root,
            str,
        ) or root == "":
            raise ValueError(
                "root must be non-empty str"
            )

        self.root = os.path.abspath(
            root
        )

        self.codec = (
            RuntimeProfileCodec()
            if codec is None
            else codec
        )

    def load(
        self,
        name,
    ):
        path = self.path_for(
            name
        )

        with open(
            path,
            "r",
            encoding="utf-8",
        ) as handle:
            text = handle.read()

        profile = (
            self.codec
            .decode_text(
                text
            )
        )

        if profile.name != name:
            raise ValueError(
                "profile name does not match filename"
            )

        return profile

    def path_for(
        self,
        name,
    ):
        if not isinstance(
            name,
            str,
        ) or name == "":
            raise ValueError(
                "profile name must be non-empty str"
            )

        if (
            "/" in name
            or "\\" in name
            or name in (
                ".",
                "..",
            )
        ):
            raise ValueError(
                "invalid runtime profile name"
            )

        filename = (
            name
            + ".json"
        )

        path = os.path.abspath(
            os.path.join(
                self.root,
                filename,
            )
        )

        prefix = (
            self.root
            + os.sep
        )

        if (
            path != self.root
            and not path.startswith(
                prefix
            )
        ):
            raise ValueError(
                "runtime profile path escapes root"
            )

        return path

    def exists(
        self,
        name,
    ):
        return os.path.isfile(
            self.path_for(
                name
            )
        )
