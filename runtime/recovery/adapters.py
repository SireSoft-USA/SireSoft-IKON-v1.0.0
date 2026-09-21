class RecoveryAdapters:
    @staticmethod
    def service_host_health_handler(
        host,
    ):
        if not isinstance(host, ServiceHost):
            raise TypeError(
                "host must be ServiceHost"
            )

        def handle(
            action,
        ):
            target = action.target

            descriptor = (
                host.discovery
                .registry
                .get(
                    target
                )
            )

            host.mark_healthy(target)
            host.enable(target)

            return {
                "instance_id": descriptor.instance_id,
                "healthy": True,
                "enabled": True,
            }

        return handle

    @staticmethod
    def worker_failure_bookkeeping_handler(
        worker_pool,
    ):
        if not isinstance(worker_pool, WorkerPool):
            raise TypeError(
                "worker_pool must be WorkerPool"
            )

        def handle(
            action,
        ):
            status = worker_pool.status()

            if (
                status["started"]
                and not status["shutdown"]
                and status["alive_workers"] > 0
            ):
                return {
                    "recovered": True,
                    "state": status,
                }

            raise RuntimeError(
                "worker pool is not in a recoverable running state"
            )

        return handle
