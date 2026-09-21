class RuntimeProfile:
    """
    Immutable typed deployment profile for the local SireLLM runtime.
    """

    def __init__(
        self,
        name,
        storage_root,
        worker_count=4,
        queue_capacity=128,
        storage_namespaces=None,
        enable_signals=True,
        host="127.0.0.1",
        port=8080,
        backlog=64,
        timeout_seconds=5.0,
        recv_chunk_bytes=4096,
        max_requests=None,
        max_idle_timeouts=None,
        metadata=None,
    ):
        if not isinstance(name, str) or name == "":
            raise ValueError(
                "name must be non-empty str"
            )

        if not isinstance(storage_root, str) or storage_root == "":
            raise ValueError(
                "storage_root must be non-empty str"
            )

        if not isinstance(worker_count, int) or worker_count <= 0:
            raise ValueError(
                "worker_count must be positive int"
            )

        if not isinstance(queue_capacity, int) or queue_capacity <= 0:
            raise ValueError(
                "queue_capacity must be positive int"
            )

        if storage_namespaces is None:
            storage_namespaces = [
                "runtime",
            ]

        if not isinstance(
            storage_namespaces,
            (list, tuple),
        ):
            raise TypeError(
                "storage_namespaces must be list/tuple or None"
            )

        normalized_namespaces = []
        seen_namespaces = {}

        for namespace in storage_namespaces:
            if not isinstance(namespace, str) or namespace == "":
                raise ValueError(
                    "storage namespace must be non-empty str"
                )

            if namespace not in seen_namespaces:
                seen_namespaces[namespace] = True
                normalized_namespaces.append(
                    namespace
                )

        if not isinstance(host, str) or host == "":
            raise ValueError(
                "host must be non-empty str"
            )

        if not isinstance(port, int) or port < 0 or port > 65535:
            raise ValueError(
                "port must be int 0..65535"
            )

        if not isinstance(backlog, int) or backlog <= 0:
            raise ValueError(
                "backlog must be positive int"
            )

        if (
            not isinstance(
                timeout_seconds,
                (int, float),
            )
            or timeout_seconds <= 0
        ):
            raise ValueError(
                "timeout_seconds must be positive"
            )

        if (
            not isinstance(
                recv_chunk_bytes,
                int,
            )
            or recv_chunk_bytes <= 0
        ):
            raise ValueError(
                "recv_chunk_bytes must be positive int"
            )

        if max_requests is not None and (
            not isinstance(max_requests, int)
            or max_requests <= 0
        ):
            raise ValueError(
                "max_requests must be positive int or None"
            )

        if max_idle_timeouts is not None and (
            not isinstance(max_idle_timeouts, int)
            or max_idle_timeouts <= 0
        ):
            raise ValueError(
                "max_idle_timeouts must be positive int or None"
            )

        if metadata is None:
            metadata = {}

        if not isinstance(metadata, dict):
            raise TypeError(
                "metadata must be dict or None"
            )

        self.name = name
        self.storage_root = storage_root
        self.worker_count = worker_count
        self.queue_capacity = queue_capacity
        self.storage_namespaces = (
            normalized_namespaces
        )
        self.enable_signals = bool(
            enable_signals
        )
        self.host = host
        self.port = port
        self.backlog = backlog
        self.timeout_seconds = float(
            timeout_seconds
        )
        self.recv_chunk_bytes = (
            recv_chunk_bytes
        )
        self.max_requests = max_requests
        self.max_idle_timeouts = (
            max_idle_timeouts
        )
        self.metadata = self._copy(
            metadata
        )

    def to_dict(
        self,
    ):
        return {
            "name": self.name,
            "storage_root": (
                self.storage_root
            ),
            "worker_count": (
                self.worker_count
            ),
            "queue_capacity": (
                self.queue_capacity
            ),
            "storage_namespaces": list(
                self.storage_namespaces
            ),
            "enable_signals": (
                self.enable_signals
            ),
            "host": self.host,
            "port": self.port,
            "backlog": self.backlog,
            "timeout_seconds": (
                self.timeout_seconds
            ),
            "recv_chunk_bytes": (
                self.recv_chunk_bytes
            ),
            "max_requests": (
                self.max_requests
            ),
            "max_idle_timeouts": (
                self.max_idle_timeouts
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
            return {
                key: self._copy(
                    value[key]
                )
                for key in value
            }

        if isinstance(
            value,
            (list, tuple),
        ):
            return [
                self._copy(
                    item
                )
                for item in value
            ]

        return value
