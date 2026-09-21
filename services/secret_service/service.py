class SecretService:
    """
    Protocol-facing secret administration service.

    Raw secret values are accepted for create/rotate but are never returned in
    any protocol response. Secret resolution is intentionally internal-only via
    SecretManager.resolve_secret().

    Supported operations:
      create
      rotate
      get
      list
      set_policy
      check_access
      enable
      disable
      destroy
      status
    """

    def __init__(
        self,
        manager=None,
    ):
        self.manager = (
            SecretManager()
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
            "secret_service"
        ):
            return self._error(
                request,
                "INVALID_REQUEST",
                "Request targeted the wrong service",
            )

        try:
            operation = (
                request.operation
            )

            if operation == "create":
                record = (
                    self.manager
                    .create_secret(
                        secret_id=self._required(
                            request.payload,
                            "secret_id",
                        ),
                        value=self._required(
                            request.payload,
                            "value",
                        ),
                        actor_id=self._required(
                            request.payload,
                            "actor_id",
                        ),
                        now=self._required(
                            request.payload,
                            "now",
                        ),
                        readers=request.payload.get(
                            "readers"
                        ),
                        writers=request.payload.get(
                            "writers"
                        ),
                        admins=request.payload.get(
                            "admins"
                        ),
                        metadata=request.payload.get(
                            "metadata"
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
                        "secret": (
                            record.public_dict()
                        ),
                    },
                )

            if operation == "rotate":
                version = (
                    self.manager
                    .rotate_secret(
                        secret_id=self._required(
                            request.payload,
                            "secret_id",
                        ),
                        value=self._required(
                            request.payload,
                            "value",
                        ),
                        actor_id=self._required(
                            request.payload,
                            "actor_id",
                        ),
                        now=self._required(
                            request.payload,
                            "now",
                        ),
                        metadata=request.payload.get(
                            "metadata"
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
                        "version": (
                            version.public_dict()
                        ),
                    },
                )

            if operation == "get":
                return self._success(
                    request,
                    {
                        "secret": (
                            self.manager
                            .public_get(
                                self._required(
                                    request.payload,
                                    "secret_id",
                                )
                            )
                        ),
                    },
                )

            if operation == "list":
                items = (
                    self.manager
                    .list_secrets()
                )

                return self._success(
                    request,
                    {
                        "secrets": items,
                        "count": len(
                            items
                        ),
                    },
                )

            if operation == "set_policy":
                record = (
                    self.manager
                    .set_policy(
                        secret_id=self._required(
                            request.payload,
                            "secret_id",
                        ),
                        actor_id=self._required(
                            request.payload,
                            "actor_id",
                        ),
                        now=self._required(
                            request.payload,
                            "now",
                        ),
                        readers=request.payload.get(
                            "readers"
                        ),
                        writers=request.payload.get(
                            "writers"
                        ),
                        admins=request.payload.get(
                            "admins"
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
                        "secret": (
                            record.public_dict()
                        ),
                    },
                )

            if operation == "check_access":
                return self._success(
                    request,
                    {
                        "access": (
                            self.manager
                            .check_access(
                                secret_id=self._required(
                                    request.payload,
                                    "secret_id",
                                ),
                                actor_id=self._required(
                                    request.payload,
                                    "actor_id",
                                ),
                                action=self._required(
                                    request.payload,
                                    "action",
                                ),
                            )
                        ),
                    },
                )

            if operation in (
                "enable",
                "disable",
                "destroy",
            ):
                method = {
                    "enable": (
                        self.manager
                        .enable_secret
                    ),
                    "disable": (
                        self.manager
                        .disable_secret
                    ),
                    "destroy": (
                        self.manager
                        .destroy_secret
                    ),
                }[
                    operation
                ]

                record = method(
                    secret_id=self._required(
                        request.payload,
                        "secret_id",
                    ),
                    actor_id=self._required(
                        request.payload,
                        "actor_id",
                    ),
                    now=self._required(
                        request.payload,
                        "now",
                    ),
                    trace_id=request.trace_id,
                    correlation_id=(
                        request.correlation_id
                    ),
                )

                return self._success(
                    request,
                    {
                        "secret": (
                            record.public_dict()
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
                    "Unsupported secret service operation"
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

        except PermissionError as error:
            return self._error(
                request,
                "FORBIDDEN",
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
