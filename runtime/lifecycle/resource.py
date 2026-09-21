class LifecycleResource:
    """
    One runtime resource managed by LifecycleManager.

    A resource declares dependencies by resource name. start_callback and
    stop_callback are synchronous callables; asynchronous/process execution is
    delegated to runtime/concurrency and runtime/processes.
    """

    STATES = (
        "registered",
        "starting",
        "running",
        "stopping",
        "stopped",
        "failed",
    )

    def __init__(
        self,
        name,
        start_callback,
        stop_callback,
        dependencies=None,
        metadata=None,
    ):
        if not isinstance(name, str) or name == "":
            raise ValueError(
                "name must be non-empty str"
            )

        if not callable(start_callback):
            raise TypeError(
                "start_callback must be callable"
            )

        if not callable(stop_callback):
            raise TypeError(
                "stop_callback must be callable"
            )

        if dependencies is None:
            dependencies = []

        if not isinstance(
            dependencies,
            (list, tuple),
        ):
            raise TypeError(
                "dependencies must be list/tuple or None"
            )

        normalized_dependencies = []

        for dependency in dependencies:
            if (
                not isinstance(
                    dependency,
                    str,
                )
                or dependency == ""
            ):
                raise ValueError(
                    "dependency names must be non-empty strings"
                )

            if dependency == name:
                raise ValueError(
                    "resource cannot depend on itself"
                )

            if dependency not in normalized_dependencies:
                normalized_dependencies.append(
                    dependency
                )

        if metadata is None:
            metadata = {}

        if not isinstance(metadata, dict):
            raise TypeError(
                "metadata must be dict or None"
            )

        self.name = name
        self.start_callback = start_callback
        self.stop_callback = stop_callback
        self.dependencies = normalized_dependencies
        self.metadata = self._copy(
            metadata
        )

        self.state = "registered"
        self.start_count = 0
        self.stop_count = 0
        self.last_error = None
        self.last_start_result = None
        self.last_stop_result = None

    def start(
        self,
    ):
        if self.state == "running":
            return self.last_start_result

        if self.state in (
            "starting",
            "stopping",
        ):
            raise RuntimeError(
                "resource is busy: "
                + self.name
            )

        self.state = "starting"
        self.last_error = None

        try:
            result = self.start_callback()

            self.last_start_result = result
            self.start_count += 1
            self.state = "running"

            return result

        except BaseException as error:
            self.last_error = str(
                error
            )
            self.state = "failed"
            raise

    def stop(
        self,
    ):
        if self.state in (
            "registered",
            "stopped",
        ):
            self.state = "stopped"
            return self.last_stop_result

        if self.state == "starting":
            raise RuntimeError(
                "cannot stop resource while starting: "
                + self.name
            )

        if self.state == "stopping":
            raise RuntimeError(
                "resource is already stopping: "
                + self.name
            )

        self.state = "stopping"

        try:
            result = self.stop_callback()

            self.last_stop_result = result
            self.stop_count += 1
            self.state = "stopped"
            self.last_error = None

            return result

        except BaseException as error:
            self.last_error = str(
                error
            )
            self.state = "failed"
            raise

    def status(
        self,
    ):
        return {
            "name": self.name,
            "state": self.state,
            "dependencies": list(
                self.dependencies
            ),
            "metadata": self._copy(
                self.metadata
            ),
            "start_count": (
                self.start_count
            ),
            "stop_count": (
                self.stop_count
            ),
            "last_error": (
                self.last_error
            ),
        }

    def _copy(
        self,
        value,
    ):
        if isinstance(value, dict):
            result = {}

            for key in value:
                result[
                    key
                ] = self._copy(
                    value[
                        key
                    ]
                )

            return result

        if isinstance(value, list):
            return [
                self._copy(
                    item
                )
                for item in value
            ]

        if isinstance(value, tuple):
            return [
                self._copy(
                    item
                )
                for item in value
            ]

        return value
