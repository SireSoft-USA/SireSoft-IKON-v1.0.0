import os


class AtomicFile:
    """
    Atomic same-directory file replacement helper.

    Writes bytes to <target>.tmp, flushes and fsyncs, then uses os.replace().
    The target is never partially written.
    """

    @staticmethod
    def write_bytes(
        path,
        temporary_path,
        data,
        overwrite=True,
    ):
        if not isinstance(path, str) or path == "":
            raise ValueError(
                "path must be non-empty str"
            )

        if not isinstance(temporary_path, str) or temporary_path == "":
            raise ValueError(
                "temporary_path must be non-empty str"
            )

        if not isinstance(data, (bytes, bytearray)):
            raise TypeError(
                "data must be bytes-like"
            )

        if (
            not overwrite
            and os.path.exists(path)
        ):
            raise FileExistsError(
                "target already exists: "
                + path
            )

        parent = os.path.dirname(
            path
        )

        if parent != "":
            os.makedirs(
                parent,
                exist_ok=True,
            )

        if os.path.exists(
            temporary_path
        ):
            os.remove(
                temporary_path
            )

        handle = open(
            temporary_path,
            "xb",
        )

        try:
            handle.write(
                bytes(data)
            )
            handle.flush()
            os.fsync(
                handle.fileno()
            )

        except Exception:
            handle.close()

            if os.path.exists(
                temporary_path
            ):
                os.remove(
                    temporary_path
                )

            raise

        finally:
            if not handle.closed:
                handle.close()

        try:
            if (
                not overwrite
                and os.path.exists(path)
            ):
                raise FileExistsError(
                    "target already exists: "
                    + path
                )

            os.replace(
                temporary_path,
                path,
            )

        except Exception:
            if os.path.exists(
                temporary_path
            ):
                os.remove(
                    temporary_path
                )

            raise

        return {
            "path": path,
            "bytes": len(
                data
            ),
        }

    @staticmethod
    def read_bytes(
        path,
    ):
        handle = open(
            path,
            "rb",
        )

        try:
            return handle.read()

        finally:
            handle.close()
