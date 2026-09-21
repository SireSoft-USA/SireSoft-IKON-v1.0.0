class NotificationManager:
    """
    Notification orchestration with templates, local channels, retries, history,
    and optional EventBus lifecycle publication.
    """

    def __init__(
        self,
        event_bus=None,
    ):
        self.event_bus = event_bus

        self._channels = {}
        self._channel_order = []

        self._templates = {}
        self._template_order = []

        self._notifications = {}
        self._notification_order = []

        self._sequence = 0

        self.total_sent = 0
        self.total_delivered = 0
        self.total_failed = 0
        self.total_cancelled = 0

    def register_channel(
        self,
        channel_id,
        handler,
        enabled=True,
        metadata=None,
    ):
        if channel_id in self._channels:
            raise ValueError(
                "notification channel already exists: "
                + str(
                    channel_id
                )
            )

        channel = NotificationChannel(
            channel_id=channel_id,
            handler=handler,
            enabled=enabled,
            metadata=metadata,
        )

        self._channels[
            channel_id
        ] = channel

        self._channel_order.append(
            channel_id
        )

        return channel

    def get_channel(
        self,
        channel_id,
    ):
        if channel_id not in self._channels:
            raise KeyError(
                "notification channel not found: "
                + str(
                    channel_id
                )
            )

        return self._channels[
            channel_id
        ]

    def list_channels(
        self,
    ):
        return [
            self._channels[
                channel_id
            ].summary()
            for channel_id
            in self._channel_order
        ]

    def create_template(
        self,
        template_id,
        body_template,
        subject_template=None,
        metadata=None,
    ):
        if template_id in self._templates:
            raise ValueError(
                "notification template already exists: "
                + str(
                    template_id
                )
            )

        template = NotificationTemplate(
            template_id=template_id,
            subject_template=(
                subject_template
            ),
            body_template=(
                body_template
            ),
            metadata=metadata,
        )

        self._templates[
            template_id
        ] = template

        self._template_order.append(
            template_id
        )

        return template

    def get_template(
        self,
        template_id,
    ):
        if template_id not in self._templates:
            raise KeyError(
                "notification template not found: "
                + str(
                    template_id
                )
            )

        return self._templates[
            template_id
        ]

    def list_templates(
        self,
    ):
        return [
            self._templates[
                template_id
            ].public_dict()
            for template_id
            in self._template_order
        ]

    def send(
        self,
        channel_id,
        recipient,
        now,
        subject=None,
        body=None,
        template_id=None,
        variables=None,
        metadata=None,
        notification_id=None,
        trace_id=None,
        correlation_id=None,
    ):
        channel = self.get_channel(
            channel_id
        )

        if template_id is not None:
            rendered = (
                self.get_template(
                    template_id
                )
                .render(
                    variables
                )
            )

            if subject is None:
                subject = rendered[
                    "subject"
                ]

            if body is None:
                body = rendered[
                    "body"
                ]

        if body is None:
            raise ValueError(
                "body or template_id is required"
            )

        if (
            not isinstance(
                now,
                int,
            )
            or now < 0
        ):
            raise ValueError(
                "now must be non-negative int"
            )

        self._sequence += 1

        if notification_id is None:
            notification_id = (
                "notification-"
                + str(
                    self._sequence
                )
            )

        if notification_id in self._notifications:
            raise ValueError(
                "duplicate notification_id: "
                + notification_id
            )

        notification = Notification(
            notification_id=(
                notification_id
            ),
            sequence=(
                self._sequence
            ),
            channel_id=channel_id,
            recipient=recipient,
            subject=subject,
            body=body,
            created_at=now,
            metadata=metadata,
            trace_id=trace_id,
            correlation_id=(
                correlation_id
            ),
        )

        self._notifications[
            notification_id
        ] = notification

        self._notification_order.append(
            notification_id
        )

        self.total_sent += 1

        self._publish_event(
            topic="notification.created",
            timestamp=now,
            notification=notification,
            extra={},
        )

        return self._deliver(
            notification,
            channel,
            now,
        )

    def retry(
        self,
        notification_id,
        now,
    ):
        notification = self.get_notification(
            notification_id
        )

        if notification.status != "failed":
            raise RuntimeError(
                "only failed notifications can be retried"
            )

        channel = self.get_channel(
            notification.channel_id
        )

        return self._deliver(
            notification,
            channel,
            now,
        )

    def cancel(
        self,
        notification_id,
        now,
    ):
        notification = self.get_notification(
            notification_id
        )

        notification.cancel(
            now
        )

        self.total_cancelled += 1

        self._publish_event(
            topic="notification.cancelled",
            timestamp=now,
            notification=notification,
            extra={},
        )

        return notification

    def get_notification(
        self,
        notification_id,
    ):
        if notification_id not in self._notifications:
            raise KeyError(
                "notification not found: "
                + str(
                    notification_id
                )
            )

        return self._notifications[
            notification_id
        ]

    def list_notifications(
        self,
        status=None,
        channel_id=None,
        recipient=None,
        limit=100,
        newest_first=False,
    ):
        if (
            not isinstance(
                limit,
                int,
            )
            or limit <= 0
        ):
            raise ValueError(
                "limit must be positive int"
            )

        if (
            status is not None
            and status
            not in Notification.VALID_STATUSES
        ):
            raise ValueError(
                "invalid notification status"
            )

        ids = list(
            self._notification_order
        )

        if newest_first:
            ids.reverse()

        result = []

        for notification_id in ids:
            item = self._notifications[
                notification_id
            ]

            if (
                status is not None
                and item.status
                != status
            ):
                continue

            if (
                channel_id is not None
                and item.channel_id
                != channel_id
            ):
                continue

            if (
                recipient is not None
                and item.recipient
                != recipient
            ):
                continue

            result.append(
                item.public_dict()
            )

            if len(
                result
            ) >= limit:
                break

        return result

    def enable_channel(
        self,
        channel_id,
    ):
        return self.get_channel(
            channel_id
        ).enable()

    def disable_channel(
        self,
        channel_id,
    ):
        return self.get_channel(
            channel_id
        ).disable()

    def status(
        self,
    ):
        counts = {
            "pending": 0,
            "delivered": 0,
            "failed": 0,
            "cancelled": 0,
        }

        for notification_id in self._notification_order:
            counts[
                self._notifications[
                    notification_id
                ].status
            ] += 1

        return {
            "ready": True,
            "channel_count": len(
                self._channel_order
            ),
            "template_count": len(
                self._template_order
            ),
            "notification_count": len(
                self._notification_order
            ),
            "counts": counts,
            "total_sent": (
                self.total_sent
            ),
            "total_delivered": (
                self.total_delivered
            ),
            "total_failed": (
                self.total_failed
            ),
            "total_cancelled": (
                self.total_cancelled
            ),
            "event_bus_attached": (
                self.event_bus
                is not None
            ),
        }

    def _deliver(
        self,
        notification,
        channel,
        now,
    ):
        notification.record_attempt()

        try:
            provider_result = (
                channel.deliver(
                    notification
                )
            )

            notification.mark_delivered(
                timestamp=now,
                provider_result=(
                    self._safe_result(
                        provider_result
                    )
                ),
            )

            self.total_delivered += 1

            self._publish_event(
                topic=(
                    "notification.delivered"
                ),
                timestamp=now,
                notification=(
                    notification
                ),
                extra={},
            )

            return {
                "notification": (
                    notification
                    .public_dict()
                ),
                "success": True,
                "error": None,
            }

        except Exception as error:
            notification.mark_failed(
                str(
                    error
                )
            )

            self.total_failed += 1

            self._publish_event(
                topic=(
                    "notification.failed"
                ),
                timestamp=now,
                notification=(
                    notification
                ),
                extra={
                    "error_type": (
                        type(
                            error
                        ).__name__
                    ),
                    "error_message": (
                        str(
                            error
                        )
                    ),
                },
            )

            return {
                "notification": (
                    notification
                    .public_dict()
                ),
                "success": False,
                "error": {
                    "type": (
                        type(
                            error
                        ).__name__
                    ),
                    "message": str(
                        error
                    ),
                },
            }

    def _publish_event(
        self,
        topic,
        timestamp,
        notification,
        extra,
    ):
        if self.event_bus is None:
            return

        if not hasattr(
            self.event_bus,
            "publish",
        ):
            raise TypeError(
                "event_bus must provide publish()"
            )

        payload = {
            "notification_id": (
                notification.notification_id
            ),
            "channel_id": (
                notification.channel_id
            ),
            "recipient": (
                notification.recipient
            ),
            "status": (
                notification.status
            ),
            "attempts": (
                notification.attempts
            ),
        }

        for key in extra:
            payload[
                key
            ] = extra[
                key
            ]

        self.event_bus.publish(
            topic=topic,
            timestamp=timestamp,
            payload=payload,
            source_service=(
                "notification_service"
            ),
            trace_id=(
                notification.trace_id
            ),
            correlation_id=(
                notification.correlation_id
            ),
        )

    def _safe_result(
        self,
        value,
    ):
        if value is None:
            return None

        if isinstance(
            value,
            (str, int, float, bool),
        ):
            return value

        if isinstance(
            value,
            list,
        ):
            return [
                self._safe_result(
                    item
                )
                for item in value
            ]

        if isinstance(
            value,
            tuple,
        ):
            return [
                self._safe_result(
                    item
                )
                for item in value
            ]

        if isinstance(
            value,
            dict,
        ):
            result = {}

            for key in value:
                if isinstance(
                    key,
                    str,
                ):
                    result[
                        key
                    ] = self._safe_result(
                        value[
                            key
                        ]
                    )

            return result

        return {
            "type": (
                type(
                    value
                ).__name__
            ),
        }
