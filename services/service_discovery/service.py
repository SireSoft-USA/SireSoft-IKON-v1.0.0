class ServiceDiscoveryService:
    """
    Protocol-facing service discovery.

    Callable local handlers are intentionally not accepted over protocol.
    Runtime code binds those through ServiceDiscoveryManager.register_local()
    or bind_local_handler().

    Supported operations:
      register
      deregister
      heartbeat
      resolve
      list_services
      get_instance
      mark_healthy
      mark_unhealthy
      enable
      disable
      sweep_stale
      status
    """

    def __init__(
        self,
        manager=None,
    ):
        self.manager = (
            ServiceDiscoveryManager()
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
            "service_discovery"
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

            if operation == "register":
                descriptor = (
                    self.manager
                    .register_instance(
                        instance_id=self._required(
                            request.payload,
                            "instance_id",
                        ),
                        service_name=self._required(
                            request.payload,
                            "service_name",
                        ),
                        endpoint=self._required(
                            request.payload,
                            "endpoint",
                        ),
                        now=self._required(
                            request.payload,
                            "now",
                        ),
                        lease_seconds=request.payload.get(
                            "lease_seconds",
                            60,
                        ),
                        metadata=request.payload.get(
                            "metadata"
                        ),
                    )
                )

                return self._success(
                    request,
                    {
                        "instance": (
                            descriptor
                            .public_dict(
                                now=request.payload[
                                    "now"
                                ]
                            )
                        ),
                    },
                )

            if operation == "deregister":
                descriptor = (
                    self.manager
                    .deregister(
                        self._required(
                            request.payload,
                            "instance_id",
                        )
                    )
                )

                return self._success(
                    request,
                    {
                        "deregistered_instance_id": (
                            descriptor.instance_id
                        ),
                    },
                )

            if operation == "heartbeat":
                descriptor = (
                    self.manager
                    .heartbeat(
                        instance_id=self._required(
                            request.payload,
                            "instance_id",
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
                        "instance": (
                            descriptor
                            .public_dict(
                                now=request.payload[
                                    "now"
                                ]
                            )
                        ),
                    },
                )

            if operation == "resolve":
                result = (
                    self.manager
                    .resolve(
                        service_name=self._required(
                            request.payload,
                            "service_name",
                        ),
                        now=self._required(
                            request.payload,
                            "now",
                        ),
                        available_only=request.payload.get(
                            "available_only",
                            True,
                        ),
                    )
                )

                return self._success(
                    request,
                    {
                        "resolution": result,
                    },
                )

            if operation == "list_services":
                services = (
                    self.manager
                    .list_services(
                        self._required(
                            request.payload,
                            "now",
                        )
                    )
                )

                return self._success(
                    request,
                    {
                        "services": services,
                        "count": len(
                            services
                        ),
                    },
                )

            if operation == "get_instance":
                descriptor = (
                    self.manager
                    .registry
                    .get(
                        self._required(
                            request.payload,
                            "instance_id",
                        )
                    )
                )

                now = request.payload.get(
                    "now"
                )

                return self._success(
                    request,
                    {
                        "instance": (
                            descriptor
                            .public_dict(
                                now=now
                            )
                        ),
                    },
                )

            if operation in (
                "mark_healthy",
                "mark_unhealthy",
                "enable",
                "disable",
            ):
                method = getattr(
                    self.manager,
                    operation,
                )

                descriptor = method(
                    self._required(
                        request.payload,
                        "instance_id",
                    )
                )

                return self._success(
                    request,
                    {
                        "instance": (
                            descriptor
                            .public_dict(
                                now=request.payload.get(
                                    "now"
                                )
                            )
                        ),
                    },
                )

            if operation == "sweep_stale":
                result = (
                    self.manager
                    .sweep_stale(
                        self._required(
                            request.payload,
                            "now",
                        )
                    )
                )

                return self._success(
                    request,
                    result,
                )

            if operation == "status":
                return self._success(
                    request,
                    {
                        "status": (
                            self.manager
                            .status(
                                self._required(
                                    request.payload,
                                    "now",
                                )
                            )
                        ),
                    },
                )

            return self._error(
                request,
                "INVALID_REQUEST",
                (
                    "Unsupported service discovery operation"
                ),
            )

        except KeyError as error:
            return self._error(
                request,
                "NOT_FOUND",
                str(error),
            )

        except RuntimeError as error:
            return self._error(
                request,
                "CONFLICT",
                str(error),
            )

        except (
            ValueError,
            TypeError,
            IndexError,
        ) as error:
            return self._error(
                request,
                "INVALID_REQUEST",
                str(error),
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
