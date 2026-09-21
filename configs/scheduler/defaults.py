def default_scheduler_config():
    return SchedulerConfig(
        tasks=[
            ScheduledTaskConfig(
                task_id="maintenance-hourly",
                queue_name="maintenance",
                payload={
                    "operation": "runtime_maintenance",
                },
                next_run_at=0,
                recurrence=SchedulerRecurrenceConfig(
                    mode="interval",
                    interval_seconds=3600,
                    catch_up=False,
                ),
                priority=0,
                max_attempts=3,
                enabled=False,
                metadata={
                    "purpose": (
                        "optional runtime maintenance cadence"
                    ),
                },
            ),
        ],
        attach_event_bus=True,
        metadata={
            "profile": "sirellm",
        },
    )
