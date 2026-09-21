class RateLimitService:
    """
    Protocol-facing rate-limit service.

    Supported operations:
      configure_policy
      remove_policy
      list_policies
      check
      consume
      reset_key
      reset_all
      bucket_state
      status
    """

    def __init__(
        self,
        manager=None,
    ):
        self.manager = (
            RateLimitManager()
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
            "rate_limit_service"
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

            if operation == "configure_policy":
                policy = (
                    self.manager
                    .configure_policy(
                        policy_id=self._required(
                            request.payload,
                            "policy_id",
                        ),
                        capacity=self._required(
                            request.payload,
                            "capacity",
                        ),
                        refill_tokens=self._required(
                            request.payload,
                            "refill_tokens",
                        ),
                        refill_seconds=self._required(
                            request.payload,
                            "refill_seconds",
                        ),
                        cost=request.payload.get(
                            "cost",
                            1,
                        ),
                        enabled=request.payload.get(
                            "enabled",
                            True,
                        ),
                        metadata=request.payload.get(
                            "metadata"
                        ),
                        replace=request.payload.get(
                            "replace",
                            False,
                        ),
                    )
                )

                return self._success(
                    request,
                    {
                        "policy": (
                            policy.to_dict()
                        ),
                    },
                )

            if operation == "remove_policy":
                policy = (
                    self.manager
                    .remove_policy(
                        self._required(
                            request.payload,
                            "policy_id",
                        )
                    )
                )

                return self._success(
                    request,
                    {
                        "removed_policy": (
                            policy.to_dict()
                        ),
                    },
                )

            if operation == "list_policies":
                policies = (
                    self.manager
                    .list_policies()
                )

                return self._success(
                    request,
                    {
                        "policies": policies,
                        "count": len(
                            policies
                        ),
                    },
                )

            if operation in (
                "check",
                "consume",
            ):
                method = (
                    self.manager.check
                    if operation == "check"
                    else self.manager.consume
                )

                result = method(
                    policy_id=self._required(
                        request.payload,
                        "policy_id",
                    ),
                    key=self._required(
                        request.payload,
                        "key",
                    ),
                    now=self._required(
                        request.payload,
                        "now",
                    ),
                    cost=request.payload.get(
                        "cost"
                    ),
                )

                return self._success(
                    request,
                    {
                        "rate_limit": result,
                    },
                )

            if operation == "reset_key":
                result = (
                    self.manager
                    .reset_key(
                        policy_id=self._required(
                            request.payload,
                            "policy_id",
                        ),
                        key=self._required(
                            request.payload,
                            "key",
                        ),
                        now=self._required(
                            request.payload,
                            "now",
                        ),
                    )
                )

                return self._success(
                    request,
                    result,
                )

            if operation == "reset_all":
                return self._success(
                    request,
                    self.manager.reset_all(),
                )

            if operation == "bucket_state":
                state = (
                    self.manager
                    .bucket_state(
                        policy_id=self._required(
                            request.payload,
                            "policy_id",
                        ),
                        key=self._required(
                            request.payload,
                            "key",
                        ),
                    )
                )

                return self._success(
                    request,
                    {
                        "bucket_state": state,
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
                    "Unsupported rate-limit service operation"
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
