class RuntimeBootstrapConfig:
    def __init__(
        self,
        storage_root,
        worker_count=4,
        queue_capacity=128,
        storage_namespaces=None,
        process_specs=None,
        process_shutdown_timeout=3.0,
        metadata=None,
    ):
        if not isinstance(storage_root, str) or storage_root == "":
            raise ValueError("storage_root must be non-empty str")

        if not isinstance(worker_count, int) or worker_count <= 0:
            raise ValueError("worker_count must be positive int")

        if not isinstance(queue_capacity, int) or queue_capacity <= 0:
            raise ValueError("queue_capacity must be positive int")

        if storage_namespaces is None:
            storage_namespaces = ["runtime"]

        if not isinstance(storage_namespaces, (list, tuple)):
            raise TypeError("storage_namespaces must be list/tuple or None")

        normalized_namespaces = []
        for namespace in storage_namespaces:
            if not isinstance(namespace, str) or namespace == "":
                raise ValueError(
                    "storage namespace names must be non-empty strings"
                )
            if namespace not in normalized_namespaces:
                normalized_namespaces.append(namespace)

        if process_specs is None:
            process_specs = []

        if not isinstance(process_specs, (list, tuple)):
            raise TypeError("process_specs must be list/tuple or None")

        normalized_specs = []
        names = []

        for spec in process_specs:
            if not isinstance(spec, ProcessSpec):
                raise TypeError("process_specs entries must be ProcessSpec")

            if spec.name in names:
                raise ValueError(
                    "duplicate process spec name: " + spec.name
                )

            names.append(spec.name)
            normalized_specs.append(spec)

        if (
            not isinstance(process_shutdown_timeout, (int, float))
            or process_shutdown_timeout <= 0
        ):
            raise ValueError("process_shutdown_timeout must be positive")

        if metadata is None:
            metadata = {}

        if not isinstance(metadata, dict):
            raise TypeError("metadata must be dict or None")

        self.storage_root = storage_root
        self.worker_count = worker_count
        self.queue_capacity = queue_capacity
        self.storage_namespaces = normalized_namespaces
        self.process_specs = normalized_specs
        self.process_shutdown_timeout = float(process_shutdown_timeout)
        self.metadata = self._copy(metadata)

    def public_dict(self):
        return {
            "storage_root": self.storage_root,
            "worker_count": self.worker_count,
            "queue_capacity": self.queue_capacity,
            "storage_namespaces": list(self.storage_namespaces),
            "process_names": [
                spec.name for spec in self.process_specs
            ],
            "process_shutdown_timeout": self.process_shutdown_timeout,
            "metadata": self._copy(self.metadata),
        }

    def _copy(self, value):
        if isinstance(value, dict):
            return {
                key: self._copy(value[key])
                for key in value
            }

        if isinstance(value, list):
            return [
                self._copy(item)
                for item in value
            ]

        if isinstance(value, tuple):
            return [
                self._copy(item)
                for item in value
            ]

        return value
