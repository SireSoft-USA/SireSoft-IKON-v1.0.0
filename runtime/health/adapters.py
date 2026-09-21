class RuntimeHealthAdapters:
    @staticmethod
    def lifecycle(
        lifecycle,
    ):
        if not isinstance(
            lifecycle,
            LifecycleManager,
        ):
            raise TypeError(
                "lifecycle must be LifecycleManager"
            )

        def check():
            status = lifecycle.status()

            phase = status[
                "phase"
            ]

            failed = status[
                "failed_resources"
            ]

            if phase == "running" and failed == 0:
                return {
                    "status": "healthy",
                    "ready": True,
                    "details": status,
                }

            if phase in (
                "created",
                "starting",
                "stopping",
                "stopped",
            ):
                return {
                    "status": "degraded",
                    "ready": False,
                    "details": status,
                }

            return {
                "status": "unhealthy",
                "ready": False,
                "details": status,
            }

        return RuntimeProbe(
            "lifecycle",
            check,
            required=True,
        )

    @staticmethod
    def worker_pool(
        worker_pool,
    ):
        if not isinstance(
            worker_pool,
            WorkerPool,
        ):
            raise TypeError(
                "worker_pool must be WorkerPool"
            )

        def check():
            status = worker_pool.status()

            if (
                status[
                    "started"
                ]
                and not status[
                    "shutdown"
                ]
                and status[
                    "alive_workers"
                ] > 0
            ):
                return {
                    "status": "healthy",
                    "ready": True,
                    "details": status,
                }

            if (
                not status[
                    "started"
                ]
                and not status[
                    "shutdown"
                ]
            ):
                return {
                    "status": "degraded",
                    "ready": False,
                    "details": status,
                }

            return {
                "status": "unhealthy",
                "ready": False,
                "details": status,
            }

        return RuntimeProbe(
            "worker_pool",
            check,
            required=True,
        )

    @staticmethod
    def storage(
        storage,
    ):
        if not isinstance(
            storage,
            RuntimeStorage,
        ):
            raise TypeError(
                "storage must be RuntimeStorage"
            )

        def check():
            status = storage.status()

            if status[
                "ready"
            ]:
                return {
                    "status": "healthy",
                    "ready": True,
                    "details": status,
                }

            return {
                "status": "unhealthy",
                "ready": False,
                "details": status,
            }

        return RuntimeProbe(
            "storage",
            check,
            required=True,
        )

    @staticmethod
    def service_host(
        host,
        now_provider,
    ):
        if not isinstance(
            host,
            ServiceHost,
        ):
            raise TypeError(
                "host must be ServiceHost"
            )

        if not callable(
            now_provider
        ):
            raise TypeError(
                "now_provider must be callable"
            )

        def check():
            status = host.status(
                now_provider()
            )

            if not status[
                "running"
            ]:
                return {
                    "status": "degraded",
                    "ready": False,
                    "details": status,
                }

            discovery = status[
                "discovery"
            ]

            if discovery is None:
                return {
                    "status": "degraded",
                    "ready": False,
                    "details": status,
                }

            if discovery[
                "available_instance_count"
            ] == discovery[
                "instance_count"
            ]:
                return {
                    "status": "healthy",
                    "ready": True,
                    "details": status,
                }

            if discovery[
                "available_instance_count"
            ] > 0:
                return {
                    "status": "degraded",
                    "ready": True,
                    "details": status,
                }

            return {
                "status": "unhealthy",
                "ready": False,
                "details": status,
            }

        return RuntimeProbe(
            "service_host",
            check,
            required=True,
        )

    @staticmethod
    def process_supervisor(
        supervisor,
    ):
        if not isinstance(
            supervisor,
            ProcessSupervisor,
        ):
            raise TypeError(
                "supervisor must be ProcessSupervisor"
            )

        def check():
            status = supervisor.status()

            rows = status[
                "processes"
            ]

            if len(rows) == 0:
                return {
                    "status": "healthy",
                    "ready": True,
                    "details": status,
                }

            running = 0
            failed = 0

            for row in rows:
                process = row[
                    "process"
                ]

                if process is None:
                    continue

                if process[
                    "running"
                ]:
                    running += 1

                if (
                    process[
                        "exit_code"
                    ]
                    is not None
                    and process[
                        "exit_code"
                    ] != 0
                ):
                    failed += 1

            if failed > 0:
                return {
                    "status": "unhealthy",
                    "ready": False,
                    "details": status,
                }

            if running == len(
                rows
            ):
                return {
                    "status": "healthy",
                    "ready": True,
                    "details": status,
                }

            return {
                "status": "degraded",
                "ready": False,
                "details": status,
            }

        return RuntimeProbe(
            "process_supervisor",
            check,
            required=False,
        )
