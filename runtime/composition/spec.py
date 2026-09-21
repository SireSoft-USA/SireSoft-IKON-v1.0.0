class RuntimeSystemSpec:
    """
    Explicit composition-root configuration for the local SireLLM runtime.

    Service bindings are in-process ServiceBinding objects. The time provider
    must return a non-negative integer runtime timestamp.
    """

    def __init__(
        self,
        storage_root,
        time_provider,
        worker_count=4,
        queue_capacity=128,
        storage_namespaces=None,
        process_specs=None,
        service_bindings=None,
        enable_signals=False,
        metadata=None,
    ):
        if not isinstance(
            storage_root,
            str,
        ) or storage_root == "":
            raise ValueError(
                "storage_root must be non-empty str"
            )

        if not callable(
            time_provider
        ):
            raise TypeError(
                "time_provider must be callable"
            )

        if (
            not isinstance(
                worker_count,
                int,
            )
            or worker_count <= 0
        ):
            raise ValueError(
                "worker_count must be positive int"
            )

        if (
            not isinstance(
                queue_capacity,
                int,
            )
            or queue_capacity <= 0
        ):
            raise ValueError(
                "queue_capacity must be positive int"
            )

        if storage_namespaces is None:
            storage_namespaces = [
                "runtime",
            ]

        if process_specs is None:
            process_specs = []

        if service_bindings is None:
            service_bindings = []

        if not isinstance(
            storage_namespaces,
            (list, tuple),
        ):
            raise TypeError(
                "storage_namespaces must be list/tuple or None"
            )

        if not isinstance(
            process_specs,
            (list, tuple),
        ):
            raise TypeError(
                "process_specs must be list/tuple or None"
            )

        if not isinstance(
            service_bindings,
            (list, tuple),
        ):
            raise TypeError(
                "service_bindings must be list/tuple or None"
            )

        normalized_bindings = []
        instance_ids = []

        for binding in service_bindings:
            if not isinstance(
                binding,
                ServiceBinding,
            ):
                raise TypeError(
                    "service_bindings entries must be ServiceBinding"
                )

            if binding.instance_id in instance_ids:
                raise ValueError(
                    "duplicate service binding instance_id: "
                    + binding.instance_id
                )

            instance_ids.append(
                binding.instance_id
            )

            normalized_bindings.append(
                binding
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

        self.storage_root = storage_root
        self.time_provider = time_provider
        self.worker_count = worker_count
        self.queue_capacity = queue_capacity
        self.storage_namespaces = list(
            storage_namespaces
        )
        self.process_specs = list(
            process_specs
        )
        self.service_bindings = (
            normalized_bindings
        )
        self.enable_signals = bool(
            enable_signals
        )
        self.metadata = self._copy(
            metadata
        )

    def now(
        self,
    ):
        value = self.time_provider()

        if (
            not isinstance(
                value,
                int,
            )
            or value < 0
        ):
            raise ValueError(
                "time_provider must return non-negative int"
            )

        return value

    def public_dict(
        self,
    ):
        return {
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
            "process_names": [
                spec.name
                for spec
                in self.process_specs
            ],
            "service_bindings": [
                binding.public_dict()
                for binding
                in self.service_bindings
            ],
            "enable_signals": (
                self.enable_signals
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
                    value[
                        key
                    ]
                )
                for key
                in value
            }

        if isinstance(
            value,
            (list, tuple),
        ):
            return [
                self._copy(
                    item
                )
                for item
                in value
            ]

        return value
