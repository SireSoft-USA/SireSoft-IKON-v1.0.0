class ConfigService:
    """
    Protocol-facing layered configuration service.

    Public operations never reveal secret config values.

    Supported operations:
      get
      resolve
      schema
      list_layers
      set_value
      unset_value
      add_layer
      remove_layer
      validate
      save_state
      load_state
      status
    """

    def __init__(
        self,
        manager,
    ):
        if manager is None or not hasattr(
            manager,
            "resolve_public",
        ):
            raise TypeError(
                "manager must provide config operations"
            )

        self.manager = manager

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
            "config_service"
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

            if operation == "get":
                result = self.manager.public_get(
                    self._required(
                        request.payload,
                        "key",
                    )
                )

                return self._success(
                    request,
                    {
                        "config": result,
                    },
                )

            if operation == "resolve":
                return self._success(
                    request,
                    {
                        "config": (
                            self.manager
                            .resolve_public()
                        ),
                        "version": (
                            self.manager
                            .version
                        ),
                    },
                )

            if operation == "schema":
                return self._success(
                    request,
                    {
                        "schema": (
                            self.manager
                            .schema
                            .public_dict()
                        ),
                    },
                )

            if operation == "list_layers":
                layers = (
                    self.manager
                    .list_layers()
                )

                return self._success(
                    request,
                    {
                        "layers": layers,
                        "count": len(
                            layers
                        ),
                    },
                )

            if operation == "set_value":
                result = (
                    self.manager
                    .set_value(
                        layer_id=self._required(
                            request.payload,
                            "layer_id",
                        ),
                        key=self._required(
                            request.payload,
                            "key",
                        ),
                        value=self._required(
                            request.payload,
                            "value",
                        ),
                    )
                )

                return self._success(
                    request,
                    {
                        "config": result,
                        "version": (
                            self.manager
                            .version
                        ),
                    },
                )

            if operation == "unset_value":
                removed = (
                    self.manager
                    .unset_value(
                        layer_id=self._required(
                            request.payload,
                            "layer_id",
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
                        "removed": removed,
                        "version": (
                            self.manager
                            .version
                        ),
                    },
                )

            if operation == "add_layer":
                layer = (
                    self.manager
                    .add_layer(
                        layer_id=self._required(
                            request.payload,
                            "layer_id",
                        ),
                        priority=self._required(
                            request.payload,
                            "priority",
                        ),
                        values=request.payload.get(
                            "values"
                        ),
                        metadata=request.payload.get(
                            "metadata"
                        ),
                    )
                )

                secret_keys = [
                    key
                    for key in (
                        self.manager
                        .schema
                        .keys()
                    )
                    if (
                        self.manager
                        .schema
                        .get(
                            key
                        )
                        .secret
                    )
                ]

                return self._success(
                    request,
                    {
                        "layer": (
                            layer.to_dict(
                                redact_keys=(
                                    secret_keys
                                )
                            )
                        ),
                        "version": (
                            self.manager
                            .version
                        ),
                    },
                )

            if operation == "remove_layer":
                layer = (
                    self.manager
                    .remove_layer(
                        self._required(
                            request.payload,
                            "layer_id",
                        )
                    )
                )

                return self._success(
                    request,
                    {
                        "removed_layer_id": (
                            layer.layer_id
                        ),
                        "version": (
                            self.manager
                            .version
                        ),
                    },
                )

            if operation == "validate":
                return self._success(
                    request,
                    self.manager.validate(),
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
                    "Unsupported config service operation"
                ),
            )

        except KeyError as error:
            return self._error(
                request,
                "NOT_FOUND",
                str(error),
            )

        except FileNotFoundError as error:
            return self._error(
                request,
                "NOT_FOUND",
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


def build_default_config_manager():
    schema = ConfigSchema(
        "sirellm-runtime"
    )

    schema.add_field(
        ConfigField(
            "environment",
            "str",
            required=True,
            default="development",
            choices=[
                "development",
                "test",
                "production",
            ],
        )
    )

    schema.add_field(
        ConfigField(
            "model_id",
            "str",
            required=True,
            default="sirellm",
        )
    )

    schema.add_field(
        ConfigField(
            "max_context_tokens",
            "int",
            required=True,
            default=512,
            minimum=1,
        )
    )

    schema.add_field(
        ConfigField(
            "retrieval_top_k",
            "int",
            required=True,
            default=5,
            minimum=1,
            maximum=100,
        )
    )

    schema.add_field(
        ConfigField(
            "auth_server_secret",
            "str",
            required=False,
            default=None,
            secret=True,
        )
    )

    return ConfigManager(
        schema=schema
    )
