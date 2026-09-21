class WorkerPoolLifecycleAdapter:
    """
    Lifecycle adapter for runtime/concurrency WorkerPool.
    """

    @staticmethod
    def resource(
        name,
        worker_pool,
        dependencies=None,
        metadata=None,
        wait_on_shutdown=True,
        cancel_pending=False,
    ):
        if not isinstance(
            worker_pool,
            WorkerPool,
        ):
            raise TypeError(
                "worker_pool must be WorkerPool"
            )

        return LifecycleResource(
            name=name,
            dependencies=dependencies,
            metadata=metadata,
            start_callback=(
                lambda: worker_pool.start()
            ),
            stop_callback=(
                lambda: worker_pool.shutdown(
                    wait=wait_on_shutdown,
                    cancel_pending=(
                        cancel_pending
                    ),
                )
            ),
        )


class ProcessSupervisorLifecycleAdapter:
    """
    Lifecycle adapter for a ProcessSupervisor.

    The supplied process names are started in order and stopped in reverse.
    """

    @staticmethod
    def resource(
        name,
        supervisor,
        process_names,
        dependencies=None,
        metadata=None,
        timeout=None,
    ):
        if not isinstance(
            supervisor,
            ProcessSupervisor,
        ):
            raise TypeError(
                "supervisor must be ProcessSupervisor"
            )

        if not isinstance(
            process_names,
            (list, tuple),
        ) or len(
            process_names
        ) == 0:
            raise ValueError(
                "process_names must be non-empty list/tuple"
            )

        names = list(
            process_names
        )

        for process_name in names:
            supervisor.registry.get_spec(
                process_name
            )

        def start_processes():
            started = []

            try:
                for process_name in names:
                    supervisor.start(
                        process_name
                    )

                    started.append(
                        process_name
                    )

                return list(
                    started
                )

            except BaseException:
                index = (
                    len(
                        started
                    )
                    - 1
                )

                while index >= 0:
                    supervisor.stop(
                        started[
                            index
                        ],
                        timeout=timeout,
                    )

                    index -= 1

                raise

        def stop_processes():
            stopped = []

            index = (
                len(
                    names
                )
                - 1
            )

            while index >= 0:
                process_name = names[
                    index
                ]

                supervisor.stop(
                    process_name,
                    timeout=timeout,
                )

                stopped.append(
                    process_name
                )

                index -= 1

            return stopped

        return LifecycleResource(
            name=name,
            dependencies=dependencies,
            metadata=metadata,
            start_callback=(
                start_processes
            ),
            stop_callback=(
                stop_processes
            ),
        )


class StorageLifecycleAdapter:
    """
    Lifecycle adapter for RuntimeStorage.

    RuntimeStorage has no open handles of its own, so starting ensures declared
    namespaces and stopping is a deterministic no-op.
    """

    @staticmethod
    def resource(
        name,
        storage,
        namespaces=None,
        dependencies=None,
        metadata=None,
    ):
        if not isinstance(
            storage,
            RuntimeStorage,
        ):
            raise TypeError(
                "storage must be RuntimeStorage"
            )

        if namespaces is None:
            namespaces = []

        if not isinstance(
            namespaces,
            (list, tuple),
        ):
            raise TypeError(
                "namespaces must be list/tuple or None"
            )

        normalized = []

        for namespace in namespaces:
            if not isinstance(
                namespace,
                str,
            ) or namespace == "":
                raise ValueError(
                    "namespace names must be non-empty strings"
                )

            normalized.append(
                namespace
            )

        def start_storage():
            for namespace in normalized:
                storage.ensure_namespace(
                    namespace
                )

            return storage.status()

        return LifecycleResource(
            name=name,
            dependencies=dependencies,
            metadata=metadata,
            start_callback=(
                start_storage
            ),
            stop_callback=(
                lambda: storage.status()
            ),
        )
