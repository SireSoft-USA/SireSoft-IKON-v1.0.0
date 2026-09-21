class SchedulerConfigValidator:
    def validate(
        self,
        config,
        job_queue=None,
    ):
        if not isinstance(
            config,
            SchedulerConfig,
        ):
            raise TypeError(
                "config must be SchedulerConfig"
            )

        errors = []
        warnings = []

        if job_queue is not None and not hasattr(
            job_queue,
            "get_queue",
        ):
            raise TypeError(
                "job_queue must provide get_queue()"
            )

        for task in config.tasks:
            if (
                task.enabled
                and job_queue is not None
            ):
                try:
                    job_queue.get_queue(
                        task.queue_name
                    )
                except Exception:
                    errors.append({
                        "code": (
                            "SCHEDULER_QUEUE_UNAVAILABLE"
                        ),
                        "task_id": task.task_id,
                        "queue_name": task.queue_name,
                        "message": (
                            "Enabled scheduled task targets an unavailable queue"
                        ),
                    })

            recurrence = task.recurrence

            if (
                recurrence.mode == "interval"
                and recurrence.interval_seconds < 5
            ):
                warnings.append({
                    "code": (
                        "VERY_SHORT_SCHEDULER_INTERVAL"
                    ),
                    "task_id": task.task_id,
                    "message": (
                        "Very short scheduler interval may produce excessive queue traffic"
                    ),
                })

            if (
                recurrence.catch_up
                and recurrence.mode == "interval"
            ):
                warnings.append({
                    "code": (
                        "CATCH_UP_RECURRENCE_ENABLED"
                    ),
                    "task_id": task.task_id,
                    "message": (
                        "Catch-up keeps the original cadence after delayed dispatch"
                    ),
                })

        if (
            config.state_path is not None
            and not config.load_state_on_start
        ):
            warnings.append({
                "code": (
                    "SCHEDULER_STATE_NOT_AUTO_LOADED"
                ),
                "message": (
                    "state_path is configured but load_state_on_start is false"
                ),
            })

        return {
            "valid": len(errors) == 0,
            "error_count": len(errors),
            "warning_count": len(warnings),
            "errors": errors,
            "warnings": warnings,
            "task_count": len(config.tasks),
            "enabled_task_count": len(
                config.enabled_tasks()
            ),
        }

    def require_valid(
        self,
        config,
        job_queue=None,
    ):
        result = self.validate(
            config,
            job_queue=job_queue,
        )

        if not result["valid"]:
            first = result["errors"][0]
            raise ValueError(
                first["code"]
                + ": "
                + first["message"]
            )

        return result
