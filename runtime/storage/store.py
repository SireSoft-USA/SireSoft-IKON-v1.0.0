import os


class RuntimeStorage:
    """
    Small filesystem-backed runtime storage layer.

    Goals:
      - namespace separation
      - traversal-safe keys
      - atomic writes
      - optional create-only semantics
      - deterministic listing
      - no serialization opinions

    Higher layers remain responsible for their own binary codecs/checksums.
    """

    def __init__(
        self,
        root_path,
        path_policy=None,
    ):
        if not isinstance(root_path, str) or root_path == "":
            raise ValueError(
                "root_path must be non-empty str"
            )

        self.root_path = root_path.rstrip(
            "/\\"
        )

        self.path_policy = (
            StoragePathPolicy(
                self.root_path
            )
            if path_policy is None
            else path_policy
        )

        self._namespaces = {}
        self._namespace_order = []

        self.total_writes = 0
        self.total_reads = 0
        self.total_deletes = 0

        os.makedirs(
            self.root_path,
            exist_ok=True,
        )

    def create_namespace(
        self,
        name,
        description="",
        metadata=None,
    ):
        self.path_policy._segment(
            name,
            "namespace",
        )

        if name in self._namespaces:
            raise ValueError(
                "namespace already exists: "
                + name
            )

        descriptor = StorageNamespace(
            name=name,
            description=description,
            metadata=metadata,
        )

        os.makedirs(
            self.path_policy
            .namespace_path(
                name
            ),
            exist_ok=True,
        )

        self._namespaces[
            name
        ] = descriptor

        self._namespace_order.append(
            name
        )

        return descriptor

    def ensure_namespace(
        self,
        name,
        description="",
        metadata=None,
    ):
        if name in self._namespaces:
            return self._namespaces[
                name
            ]

        return self.create_namespace(
            name,
            description=description,
            metadata=metadata,
        )

    def put(
        self,
        namespace,
        key,
        data,
        overwrite=True,
    ):
        self._require_namespace(
            namespace
        )

        path = (
            self.path_policy
            .key_path(
                namespace,
                key,
            )
        )

        temporary = (
            self.path_policy
            .temporary_path(
                namespace,
                key,
            )
        )

        result = AtomicFile.write_bytes(
            path,
            temporary,
            data,
            overwrite=overwrite,
        )

        self.total_writes += 1

        return result

    def get(
        self,
        namespace,
        key,
    ):
        self._require_namespace(
            namespace
        )

        path = (
            self.path_policy
            .key_path(
                namespace,
                key,
            )
        )

        if not os.path.exists(
            path
        ):
            raise KeyError(
                "storage key not found: "
                + namespace
                + "/"
                + key
            )

        data = AtomicFile.read_bytes(
            path
        )

        self.total_reads += 1

        return data

    def exists(
        self,
        namespace,
        key,
    ):
        self._require_namespace(
            namespace
        )

        return os.path.exists(
            self.path_policy
            .key_path(
                namespace,
                key,
            )
        )

    def delete(
        self,
        namespace,
        key,
        missing_ok=False,
    ):
        self._require_namespace(
            namespace
        )

        path = (
            self.path_policy
            .key_path(
                namespace,
                key,
            )
        )

        if not os.path.exists(
            path
        ):
            if missing_ok:
                return False

            raise KeyError(
                "storage key not found: "
                + namespace
                + "/"
                + key
            )

        os.remove(
            path
        )

        self.total_deletes += 1

        return True

    def list_keys(
        self,
        namespace,
    ):
        self._require_namespace(
            namespace
        )

        directory = (
            self.path_policy
            .namespace_path(
                namespace
            )
        )

        if not os.path.exists(
            directory
        ):
            return []

        result = []

        for name in os.listdir(
            directory
        ):
            if name.endswith(
                ".tmp"
            ):
                continue

            if not name.endswith(
                self.path_policy
                .extension
            ):
                continue

            path = (
                directory
                + "/"
                + name
            )

            if not os.path.isfile(
                path
            ):
                continue

            key = name[
                : -len(
                    self.path_policy
                    .extension
                )
            ]

            result.append(
                key
            )

        result.sort()

        return result

    def key_info(
        self,
        namespace,
        key,
    ):
        self._require_namespace(
            namespace
        )

        path = (
            self.path_policy
            .key_path(
                namespace,
                key,
            )
        )

        if not os.path.exists(
            path
        ):
            raise KeyError(
                "storage key not found: "
                + namespace
                + "/"
                + key
            )

        return {
            "namespace": (
                namespace
            ),
            "key": key,
            "path": path,
            "bytes": os.path.getsize(
                path
            ),
        }

    def list_namespaces(
        self,
    ):
        return [
            self._namespaces[
                name
            ].to_dict()
            for name
            in self._namespace_order
        ]

    def status(
        self,
    ):
        key_count = 0

        for name in self._namespace_order:
            key_count += len(
                self.list_keys(
                    name
                )
            )

        return {
            "ready": True,
            "root_path": (
                self.root_path
            ),
            "namespace_count": len(
                self._namespace_order
            ),
            "key_count": (
                key_count
            ),
            "total_writes": (
                self.total_writes
            ),
            "total_reads": (
                self.total_reads
            ),
            "total_deletes": (
                self.total_deletes
            ),
            "atomic_replace": True,
        }

    def _require_namespace(
        self,
        namespace,
    ):
        self.path_policy._segment(
            namespace,
            "namespace",
        )

        if namespace not in self._namespaces:
            raise KeyError(
                "storage namespace not found: "
                + str(
                    namespace
                )
            )

        return self._namespaces[
            namespace
        ]
