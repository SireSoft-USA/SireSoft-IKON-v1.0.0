class FeatureFlagService:
    """
    Protocol-facing feature-flag service.

    Supported operations:
      create_flag
      delete_flag
      get_flag
      list_flags
      set_enabled
      add_rule
      remove_rule
      evaluate
      save_state
      load_state
      status
    """

    def __init__(
        self,
        manager=None,
    ):
        self.manager = (
            FeatureFlagManager()
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
            "feature_flag_service"
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

            if operation == "create_flag":
                flag = (
                    self.manager
                    .create_flag(
                        flag_key=self._required(
                            request.payload,
                            "flag_key",
                        ),
                        variants=self._required(
                            request.payload,
                            "variants",
                        ),
                        default_variant=self._required(
                            request.payload,
                            "default_variant",
                        ),
                        disabled_variant=self._required(
                            request.payload,
                            "disabled_variant",
                        ),
                        enabled=request.payload.get(
                            "enabled",
                            True,
                        ),
                        description=request.payload.get(
                            "description",
                            "",
                        ),
                        metadata=request.payload.get(
                            "metadata"
                        ),
                        timestamp=request.payload.get(
                            "timestamp"
                        ),
                    )
                )

                return self._success(
                    request,
                    {
                        "flag": (
                            flag.public_dict()
                        ),
                    },
                )

            if operation == "delete_flag":
                flag = (
                    self.manager
                    .delete_flag(
                        flag_key=self._required(
                            request.payload,
                            "flag_key",
                        ),
                        timestamp=request.payload.get(
                            "timestamp"
                        ),
                    )
                )

                return self._success(
                    request,
                    {
                        "deleted_flag_key": (
                            flag.flag_key
                        ),
                    },
                )

            if operation == "get_flag":
                flag = (
                    self.manager
                    .get_flag(
                        self._required(
                            request.payload,
                            "flag_key",
                        )
                    )
                )

                return self._success(
                    request,
                    {
                        "flag": (
                            flag.public_dict()
                        ),
                    },
                )

            if operation == "list_flags":
                flags = (
                    self.manager
                    .list_flags()
                )

                return self._success(
                    request,
                    {
                        "flags": flags,
                        "count": len(
                            flags
                        ),
                    },
                )

            if operation == "set_enabled":
                flag = (
                    self.manager
                    .set_enabled(
                        flag_key=self._required(
                            request.payload,
                            "flag_key",
                        ),
                        enabled=self._required(
                            request.payload,
                            "enabled",
                        ),
                        timestamp=request.payload.get(
                            "timestamp"
                        ),
                    )
                )

                return self._success(
                    request,
                    {
                        "flag": (
                            flag.public_dict()
                        ),
                    },
                )

            if operation == "add_rule":
                rule = (
                    self.manager
                    .add_rule(
                        flag_key=self._required(
                            request.payload,
                            "flag_key",
                        ),
                        rule_id=self._required(
                            request.payload,
                            "rule_id",
                        ),
                        conditions=request.payload.get(
                            "conditions"
                        ),
                        variant=request.payload.get(
                            "variant"
                        ),
                        rollout_basis_points=request.payload.get(
                            "rollout_basis_points"
                        ),
                        rollout_variant=request.payload.get(
                            "rollout_variant"
                        ),
                        salt=request.payload.get(
                            "salt",
                            "",
                        ),
                        enabled=request.payload.get(
                            "enabled",
                            True,
                        ),
                        metadata=request.payload.get(
                            "metadata"
                        ),
                        timestamp=request.payload.get(
                            "timestamp"
                        ),
                    )
                )

                return self._success(
                    request,
                    {
                        "rule": (
                            rule.public_dict()
                        ),
                    },
                )

            if operation == "remove_rule":
                rule = (
                    self.manager
                    .remove_rule(
                        flag_key=self._required(
                            request.payload,
                            "flag_key",
                        ),
                        rule_id=self._required(
                            request.payload,
                            "rule_id",
                        ),
                        timestamp=request.payload.get(
                            "timestamp"
                        ),
                    )
                )

                return self._success(
                    request,
                    {
                        "removed_rule_id": (
                            rule.rule_id
                        ),
                    },
                )

            if operation == "evaluate":
                result = (
                    self.manager
                    .evaluate(
                        flag_key=self._required(
                            request.payload,
                            "flag_key",
                        ),
                        subject_key=self._required(
                            request.payload,
                            "subject_key",
                        ),
                        attributes=request.payload.get(
                            "attributes"
                        ),
                    )
                )

                return self._success(
                    request,
                    {
                        "evaluation": (
                            result
                        ),
                    },
                )

            if operation == "save_state":
                info = (
                    self.manager
                    .save_state(
                        self._required(
                            request.payload,
                            "path",
                        )
                    )
                )

                return self._success(
                    request,
                    {
                        "artifact": info,
                    },
                )

            if operation == "load_state":
                info = (
                    self.manager
                    .load_state_file(
                        self._required(
                            request.payload,
                            "path",
                        )
                    )
                )

                return self._success(
                    request,
                    {
                        "status": info,
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
                    "Unsupported feature-flag service operation"
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

        except FileNotFoundError as error:
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
