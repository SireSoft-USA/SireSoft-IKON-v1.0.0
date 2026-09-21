def default_notification_config():
    return NotificationConfig(
        channels=[
            NotificationChannelConfig(
                channel_id="in_app",
                handler_key="in_app",
                enabled=True,
                required_handler=True,
                metadata={
                    "transport": "local",
                },
            ),
            NotificationChannelConfig(
                channel_id="email",
                handler_key="email",
                enabled=False,
                required_handler=False,
                metadata={
                    "transport": (
                        "runtime-adapter"
                    ),
                },
            ),
        ],
        templates=[
            NotificationTemplateConfig(
                template_id=(
                    "job-completed"
                ),
                subject_template=(
                    "Job {{job_id}} completed"
                ),
                body_template=(
                    "Job {{job_id}} completed successfully."
                ),
                enabled=True,
            ),
            NotificationTemplateConfig(
                template_id=(
                    "job-failed"
                ),
                subject_template=(
                    "Job {{job_id}} failed"
                ),
                body_template=(
                    "Job {{job_id}} failed: {{reason}}"
                ),
                enabled=True,
            ),
        ],
        attach_event_bus=True,
        metadata={
            "profile": "sirellm",
        },
    )
