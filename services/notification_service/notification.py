class Notification:
    """
    Deterministic notification envelope.

    Channel handlers are responsible only for delivery. The notification core
    tracks recipient, content, attempts, delivery state, trace metadata, and
    failure information without relying on external libraries.
    """

    VALID_STATUSES = (
        "pending",
        "delivered",
        "failed",
        "cancelled",
    )

    def __init__(
        self,
        notification_id,
        sequence,
        channel_id,
        recipient,
        subject,
        body,
        created_at,
        metadata=None,
        trace_id=None,
        correlation_id=None,
    ):
        if not isinstance(
            notification_id,
            str,
        ) or notification_id == "":
            raise ValueError(
                "notification_id must be non-empty str"
            )

        if (
            not isinstance(
                sequence,
                int,
            )
            or sequence <= 0
        ):
            raise ValueError(
                "sequence must be positive int"
            )

        if not isinstance(
            channel_id,
            str,
        ) or channel_id == "":
            raise ValueError(
                "channel_id must be non-empty str"
            )

        if not isinstance(
            recipient,
            str,
        ) or recipient == "":
            raise ValueError(
                "recipient must be non-empty str"
            )

        if subject is not None and not isinstance(
            subject,
            str,
        ):
            raise TypeError(
                "subject must be str or None"
            )

        if not isinstance(
            body,
            str,
        ):
            raise TypeError(
                "body must be str"
            )

        if (
            not isinstance(
                created_at,
                int,
            )
            or created_at < 0
        ):
            raise ValueError(
                "created_at must be non-negative int"
            )

        if metadata is None:
            metadata = {}

        if not isinstance(
            metadata,
            dict,
        ):
            raise TypeError(
                "metadata must be dict or None"
            )

        self.notification_id = (
            notification_id
        )
        self.sequence = sequence
        self.channel_id = channel_id
        self.recipient = recipient
        self.subject = subject
        self.body = body
        self.created_at = created_at
        self.metadata = self._copy(
            metadata
        )
        self.trace_id = trace_id
        self.correlation_id = (
            correlation_id
        )

        self.status = "pending"
        self.attempts = 0
        self.delivered_at = None
        self.cancelled_at = None
        self.last_error = None
        self.provider_result = None

    def record_attempt(
        self,
    ):
        if self.status == "cancelled":
            raise RuntimeError(
                "cancelled notification cannot be delivered"
            )

        if self.status == "delivered":
            raise RuntimeError(
                "delivered notification cannot be delivered again"
            )

        self.attempts += 1
        self.status = "pending"

        return self

    def mark_delivered(
        self,
        timestamp,
        provider_result=None,
    ):
        self._validate_time(
            timestamp
        )

        self.status = "delivered"
        self.delivered_at = (
            timestamp
        )
        self.last_error = None
        self.provider_result = (
            self._copy(
                provider_result
            )
        )

        return self

    def mark_failed(
        self,
        error_message,
    ):
        if not isinstance(
            error_message,
            str,
        ):
            raise TypeError(
                "error_message must be str"
            )

        self.status = "failed"
        self.last_error = (
            error_message
        )

        return self

    def cancel(
        self,
        timestamp,
    ):
        self._validate_time(
            timestamp
        )

        if self.status == "delivered":
            raise RuntimeError(
                "delivered notification cannot be cancelled"
            )

        self.status = "cancelled"
        self.cancelled_at = (
            timestamp
        )

        return self

    def public_dict(
        self,
    ):
        return {
            "notification_id": (
                self.notification_id
            ),
            "sequence": (
                self.sequence
            ),
            "channel_id": (
                self.channel_id
            ),
            "recipient": (
                self.recipient
            ),
            "subject": (
                self.subject
            ),
            "body": self.body,
            "created_at": (
                self.created_at
            ),
            "metadata": self._copy(
                self.metadata
            ),
            "trace_id": (
                self.trace_id
            ),
            "correlation_id": (
                self.correlation_id
            ),
            "status": (
                self.status
            ),
            "attempts": (
                self.attempts
            ),
            "delivered_at": (
                self.delivered_at
            ),
            "cancelled_at": (
                self.cancelled_at
            ),
            "last_error": (
                self.last_error
            ),
            "provider_result": (
                self._copy(
                    self.provider_result
                )
            ),
        }

    def _validate_time(
        self,
        value,
    ):
        if (
            not isinstance(
                value,
                int,
            )
            or value < 0
        ):
            raise ValueError(
                "timestamp must be non-negative int"
            )

    def _copy(
        self,
        value,
    ):
        if isinstance(
            value,
            dict,
        ):
            result = {}

            for key in value:
                result[
                    key
                ] = self._copy(
                    value[
                        key
                    ]
                )

            return result

        if isinstance(
            value,
            list,
        ):
            return [
                self._copy(
                    item
                )
                for item in value
            ]

        if isinstance(
            value,
            tuple,
        ):
            return [
                self._copy(
                    item
                )
                for item in value
            ]

        return value
