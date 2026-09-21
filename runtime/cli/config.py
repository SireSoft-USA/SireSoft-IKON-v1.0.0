class RuntimeCLIConfig:
    """
    Typed runtime-launch configuration derived from RuntimeCLICommand.
    """

    def __init__(
        self,
        storage_root,
        worker_count=4,
        queue_capacity=128,
        storage_namespaces=None,
        enable_signals=False,
        wait_timeout=None,
    ):
        if not isinstance(
            storage_root,
            str,
        ) or storage_root == "":
            raise ValueError(
                "storage_root must be non-empty str"
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

        if not isinstance(
            storage_namespaces,
            list,
        ) or len(
            storage_namespaces
        ) == 0:
            raise ValueError(
                "storage_namespaces must be non-empty list"
            )

        seen = {}
        normalized = []

        for name in storage_namespaces:
            if (
                not isinstance(
                    name,
                    str,
                )
                or name == ""
            ):
                raise ValueError(
                    "storage namespace must be non-empty str"
                )

            if name not in seen:
                seen[
                    name
                ] = True
                normalized.append(
                    name
                )

        if wait_timeout is not None and (
            not isinstance(
                wait_timeout,
                (int, float),
            )
            or wait_timeout < 0
        ):
            raise ValueError(
                "wait_timeout must be non-negative numeric or None"
            )

        self.storage_root = storage_root
        self.worker_count = worker_count
        self.queue_capacity = queue_capacity
        self.storage_namespaces = normalized
        self.enable_signals = bool(
            enable_signals
        )
        self.wait_timeout = wait_timeout

    @staticmethod
    def from_command(
        command,
        default_storage_root="runtime-data",
    ):
        if not isinstance(
            command,
            RuntimeCLICommand,
        ):
            raise TypeError(
                "command must be RuntimeCLICommand"
            )

        storage_root = command.option(
            "storage-root",
            default_storage_root,
        )

        worker_count = (
            RuntimeCLIConfig
            ._positive_int(
                command.option(
                    "workers",
                    "4",
                ),
                "workers",
            )
        )

        queue_capacity = (
            RuntimeCLIConfig
            ._positive_int(
                command.option(
                    "queue-capacity",
                    "128",
                ),
                "queue-capacity",
            )
        )

        namespaces = command.option(
            "namespace",
            [
                "runtime",
            ],
        )

        wait_raw = command.option(
            "wait-timeout"
        )

        wait_timeout = None

        if wait_raw is not None:
            wait_timeout = (
                RuntimeCLIConfig
                ._non_negative_number(
                    wait_raw,
                    "wait-timeout",
                )
            )

        return RuntimeCLIConfig(
            storage_root=storage_root,
            worker_count=worker_count,
            queue_capacity=(
                queue_capacity
            ),
            storage_namespaces=list(
                namespaces
            ),
            enable_signals=bool(
                command.option(
                    "enable-signals",
                    False,
                )
            ),
            wait_timeout=(
                wait_timeout
            ),
        )

    def to_dict(
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
            "enable_signals": (
                self.enable_signals
            ),
            "wait_timeout": (
                self.wait_timeout
            ),
        }

    @staticmethod
    def _positive_int(
        text,
        name,
    ):
        try:
            value = int(
                text
            )

        except (
            ValueError,
            TypeError,
        ):
            raise ValueError(
                name
                + " must be positive integer"
            )

        if value <= 0:
            raise ValueError(
                name
                + " must be positive integer"
            )

        return value

    @staticmethod
    def _non_negative_number(
        text,
        name,
    ):
        try:
            if "." in str(
                text
            ):
                value = float(
                    text
                )
            else:
                value = int(
                    text
                )

        except (
            ValueError,
            TypeError,
        ):
            raise ValueError(
                name
                + " must be non-negative number"
            )

        if value < 0:
            raise ValueError(
                name
                + " must be non-negative number"
            )

        return value
