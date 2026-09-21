class NotificationConfigValidator:
    def validate(
        self,
        config,
    ):
        if not isinstance(
            config,
            NotificationConfig,
        ):
            raise TypeError(
                "config must be NotificationConfig"
            )

        errors = []
        warnings = []

        enabled_channels = (
            config.enabled_channels()
        )

        if len(
            enabled_channels
        ) == 0:
            errors.append({
                "code": (
                    "NO_ENABLED_NOTIFICATION_CHANNELS"
                ),
                "message": (
                    "At least one notification channel must be enabled"
                ),
            })

        for channel in config.channels:
            if (
                channel.enabled
                and not channel
                .required_handler
            ):
                warnings.append({
                    "code": (
                        "ENABLED_OPTIONAL_NOTIFICATION_HANDLER"
                    ),
                    "channel_id": (
                        channel.channel_id
                    ),
                    "message": (
                        "Enabled channel may be skipped if its optional runtime handler is absent"
                    ),
                })

        for template in config.enabled_templates():
            combined = (
                template.body_template
            )

            if (
                template.subject_template
                is not None
            ):
                combined = (
                    template
                    .subject_template
                    + "\n"
                    + combined
                )

            if "{{" in combined and "}}" not in combined:
                warnings.append({
                    "code": (
                        "POSSIBLE_UNCLOSED_TEMPLATE_PLACEHOLDER"
                    ),
                    "template_id": (
                        template.template_id
                    ),
                    "message": (
                        "Template may contain an unclosed placeholder"
                    ),
                })

            if (
                template.body_template
                == ""
            ):
                warnings.append({
                    "code": (
                        "EMPTY_NOTIFICATION_BODY_TEMPLATE"
                    ),
                    "template_id": (
                        template.template_id
                    ),
                    "message": (
                        "Enabled notification template has an empty body"
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
            "enabled_channel_count": (
                len(
                    enabled_channels
                )
            ),
            "enabled_template_count": (
                len(
                    config.enabled_templates()
                )
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
