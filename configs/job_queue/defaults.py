def default_job_queue_config():
    return JobQueueConfig(
        queues=[
            JobQueueDefinitionConfig(
                queue_name="training",
                default_lease_seconds=300,
                default_max_attempts=2,
                metadata={
                    "purpose": (
                        "long-running model training work"
                    ),
                },
            ),
            JobQueueDefinitionConfig(
                queue_name="preprocessing",
                default_lease_seconds=120,
                default_max_attempts=3,
            ),
            JobQueueDefinitionConfig(
                queue_name="maintenance",
                default_lease_seconds=60,
                default_max_attempts=3,
            ),
            JobQueueDefinitionConfig(
                queue_name="notifications",
                default_lease_seconds=30,
                default_max_attempts=5,
            ),
        ],
        workers=[],
        attach_event_bus=True,
        metadata={
            "profile": "sirellm",
        },
    )
