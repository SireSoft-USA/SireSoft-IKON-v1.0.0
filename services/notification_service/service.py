class NotificationService:
    """
    Protocol-facing notification service.

    Runtime channel handlers are registered directly on NotificationManager;
    callable transport implementations do not cross the protocol boundary.

    Supported operations:
      create_template
      get_template
      list_templates
      list_channels
      send
      retry
      cancel
      get_notification
      list_notifications
      enable_channel
      disable_channel
      status
    """

    def __init__(
        self,
        manager=None,
    ):
        self.manager = (
            NotificationManager()
            if manager is None
            else manager
        )

    def handle(
        self,
        request,
    ):
        if not isinstance(
            request,
            ServiceRequest,
        ):
            raise TypeError(
                "request must be ServiceRequest"
            )

        if request.service != (
            "notification_service"
        ):
            return self._error(
                request,
                "INVALID_REQUEST",
                "Request targeted the wrong service",
            )

        try:
            operation = request.operation

            if operation == "create_template":
                template = (
                    self.manager
                    .create_template(
                        template_id=self._required(
                            request.payload,
                            "template_id",
                        ),
                        body_template=self._required(
                            request.payload,
                            "body_template",
                        ),
                        subject_template=request.payload.get(
                            "subject_template"
                        ),
                        metadata=request.payload.get(
                            "metadata"
                        ),
                    )
                )

                return self._success(
                    request,
                    {
                        "template": (
                            template
                            .public_dict()
                        ),
                    },
                )

            if operation == "get_template":
                template = (
                    self.manager
                    .get_template(
                        self._required(
                            request.payload,
                            "template_id",
                        )
                    )
                )

                return self._success(
                    request,
                    {
                        "template": (
                            template
                            .public_dict()
                        ),
                    },
                )

            if operation == "list_templates":
                templates = (
                    self.manager
                    .list_templates()
                )

                return self._success(
                    request,
                    {
                        "templates": templates,
                        "count": len(
                            templates
                        ),
                    },
                )

            if operation == "list_channels":
                channels = (
                    self.manager
                    .list_channels()
                )

                return self._success(
                    request,
                    {
                        "channels": channels,
                        "count": len(
                            channels
                        ),
                    },
                )

            if operation == "send":
                result = (
                    self.manager
                    .send(
                        channel_id=self._required(
                            request.payload,
                            "channel_id",
                        ),
                        recipient=self._required(
                            request.payload,
                            "recipient",
                        ),
                        now=self._required(
                            request.payload,
                            "now",
                        ),
                        subject=request.payload.get(
                            "subject"
                        ),
                        body=request.payload.get(
                            "body"
                        ),
                        template_id=request.payload.get(
                            "template_id"
                        ),
                        variables=request.payload.get(
                            "variables"
                        ),
                        metadata=request.payload.get(
                            "metadata"
                        ),
                        notification_id=request.payload.get(
                            "notification_id"
                        ),
                        trace_id=request.trace_id,
                        correlation_id=(
                            request.correlation_id
                        ),
                    )
                )

                return self._success(
                    request,
                    {
                        "delivery": result,
                    },
                )

            if operation == "retry":
                result = (
                    self.manager
                    .retry(
                        notification_id=self._required(
                            request.payload,
                            "notification_id",
                        ),
                        now=self._required(
                            request.payload,
                            "now",
                        ),
                    )
                )

                return self._success(
                    request,
                    {
                        "delivery": result,
                    },
                )

            if operation == "cancel":
                notification = (
                    self.manager
                    .cancel(
                        notification_id=self._required(
                            request.payload,
                            "notification_id",
                        ),
                        now=self._required(
                            request.payload,
                            "now",
                        ),
                    )
                )

                return self._success(
                    request,
                    {
                        "notification": (
                            notification
                            .public_dict()
                        ),
                    },
                )

            if operation == "get_notification":
                notification = (
                    self.manager
                    .get_notification(
                        self._required(
                            request.payload,
                            "notification_id",
                        )
                    )
                )

                return self._success(
                    request,
                    {
                        "notification": (
                            notification
                            .public_dict()
                        ),
                    },
                )

            if operation == "list_notifications":
                notifications = (
                    self.manager
                    .list_notifications(
                        status=request.payload.get(
                            "status"
                        ),
                        channel_id=request.payload.get(
                            "channel_id"
                        ),
                        recipient=request.payload.get(
                            "recipient"
                        ),
                        limit=request.payload.get(
                            "limit",
                            100,
                        ),
                        newest_first=request.payload.get(
                            "newest_first",
                            False,
                        ),
                    )
                )

                return self._success(
                    request,
                    {
                        "notifications": (
                            notifications
                        ),
                        "count": len(
                            notifications
                        ),
                    },
                )

            if operation in (
                "enable_channel",
                "disable_channel",
            ):
                method = (
                    self.manager.enable_channel
                    if operation
                    == "enable_channel"
                    else self.manager.disable_channel
                )

                channel = method(
                    self._required(
                        request.payload,
                        "channel_id",
                    )
                )

                return self._success(
                    request,
                    {
                        "channel": (
                            channel.summary()
                        ),
                    },
                )

            if operation == "status":
                return self._success(
                    request,
                    {
                        "status": (
                            self.manager
                            .status()
                        ),
                    },
                )

            return self._error(
                request,
                "INVALID_REQUEST",
                (
                    "Unsupported notification service operation"
                ),
            )

        except KeyError as error:
            return self._error(
                request,
                "NOT_FOUND",
                str(
                    error
                ),
            )

        except RuntimeError as error:
            return self._error(
                request,
                "CONFLICT",
                str(
                    error
                ),
            )

        except (
            ValueError,
            TypeError,
            IndexError,
        ) as error:
            return self._error(
                request,
                "INVALID_REQUEST",
                str(
                    error
                ),
            )

    def _required(
        self,
        payload,
        key,
    ):
        if key not in payload:
            raise ValueError(
                "payload requires "
                + key
            )

        return payload[
            key
        ]

    def _success(
        self,
        request,
        data,
    ):
        return (
            ServiceResponse
            .success_response(
                request,
                data=data,
            )
        )

    def _error(
        self,
        request,
        code,
        message,
    ):
        return (
            ServiceResponse
            .error_response(
                request,
                ProtocolError(
                    code=code,
                    message=message,
                    retryable=False,
                ),
            )
        )
