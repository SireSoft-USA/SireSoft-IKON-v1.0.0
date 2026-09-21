class JobQueueConfigValidator:
    def validate(
        self,
        config,
    ):
        if not isinstance(
            config,
            JobQueueConfig,
        ):
            raise TypeError(
                "config must be JobQueueConfig"
            )

        errors = []
        warnings = []

        enabled_queues = (
            config.enabled_queues()
        )

        enabled_names = {
            queue.queue_name: True
            for queue
            in enabled_queues
        }

        if len(
            enabled_queues
        ) == 0:
            errors.append({
                "code": (
                    "NO_ENABLED_JOB_QUEUES"
                ),
                "message": (
                    "At least one queue must be enabled"
                ),
            })

        for worker in (
            config.enabled_workers()
        ):
            if (
                worker.queue_name
                not in enabled_names
            ):
                errors.append({
                    "code": (
                        "WORKER_QUEUE_UNAVAILABLE"
                    ),
                    "worker_id": (
                        worker.worker_id
                    ),
                    "queue_name": (
                        worker.queue_name
                    ),
                    "message": (
                        "Enabled worker targets a missing or disabled queue"
                    ),
                })

        for queue in enabled_queues:
            if (
                queue
                .default_lease_seconds
                < 5
            ):
                warnings.append({
                    "code": (
                        "VERY_SHORT_JOB_LEASE"
                    ),
                    "queue_name": (
                        queue.queue_name
                    ),
                    "message": (
                        "Very short lease may cause premature recovery"
                    ),
                })

            if (
                queue
                .default_max_attempts
                > 10
            ):
                warnings.append({
                    "code": (
                        "HIGH_JOB_RETRY_LIMIT"
                    ),
                    "queue_name": (
                        queue.queue_name
                    ),
                    "message": (
                        "High retry count may delay dead-lettering"
                    ),
                })

        if (
            config.state_path
            is not None
            and not config
            .load_state_on_start
        ):
            warnings.append({
                "code": (
                    "STATE_PATH_NOT_AUTO_LOADED"
                ),
                "message": (
                    "state_path is configured but load_state_on_start is false"
                ),
            })

        return {
            "valid": (
                len(
                    errors
                )
                == 0
            ),
            "error_count": len(
                errors
            ),
            "warning_count": len(
                warnings
            ),
            "errors": errors,
            "warnings": warnings,
            "enabled_queue_count": len(
                enabled_queues
            ),
            "enabled_worker_count": len(
                config.enabled_workers()
            ),
        }

    def require_valid(
        self,
        config,
    ):
        result = self.validate(
            config
        )

        if not result[
            "valid"
        ]:
            first = result[
                "errors"
            ][0]

            raise ValueError(
                first[
                    "code"
                ]
                + ": "
                + first[
                    "message"
                ]
            )

        return result
