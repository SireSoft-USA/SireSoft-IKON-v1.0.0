class ModelRegistryService:
    """
    Protocol-facing model registry.

    Supported operations:
      register_checkpoint
      list_models
      list_versions
      get_version
      stage_version
      promote_version
      deprecate_version
      active_version
      verify_version
      discover_checkpoints
      export_registry
      load_registry
    """

    def __init__(
        self,
        registry=None,
    ):
        self.registry = (
            ModelRegistry()
            if registry is None
            else registry
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

        if request.service != "model_registry":
            return self._error(
                request,
                "INVALID_REQUEST",
                "Request targeted the wrong service",
            )

        try:
            operation = request.operation

            if operation == "register_checkpoint":
                item = (
                    self.registry
                    .register_checkpoint(
                        model_id=self._required(
                            request.payload,
                            "model_id",
                        ),
                        version=self._required(
                            request.payload,
                            "version",
                        ),
                        checkpoint_path=self._required(
                            request.payload,
                            "checkpoint_path",
                        ),
                        metadata=request.payload.get(
                            "metadata"
                        ),
                        stage=bool(
                            request.payload.get(
                                "stage",
                                False,
                            )
                        ),
                    )
                )

                return self._success(
                    request,
                    {
                        "model_version": item.to_dict(),
                    },
                )

            if operation == "list_models":
                models = (
                    self.registry
                    .models()
                )

                return self._success(
                    request,
                    {
                        "models": models,
                        "count": len(
                            models
                        ),
                    },
                )

            if operation == "list_versions":
                model_id = self._required(
                    request.payload,
                    "model_id",
                )

                versions = [
                    item.to_dict()
                    for item in self.registry.versions(
                        model_id,
                        include_deprecated=bool(
                            request.payload.get(
                                "include_deprecated",
                                True,
                            )
                        ),
                    )
                ]

                return self._success(
                    request,
                    {
                        "model_id": model_id,
                        "versions": versions,
                        "count": len(
                            versions
                        ),
                    },
                )

            if operation == "get_version":
                item = self.registry.get(
                    self._required(
                        request.payload,
                        "model_id",
                    ),
                    self._required(
                        request.payload,
                        "version",
                    ),
                )

                return self._success(
                    request,
                    {
                        "model_version": item.to_dict(),
                    },
                )

            if operation == "stage_version":
                item = self.registry.stage(
                    self._required(
                        request.payload,
                        "model_id",
                    ),
                    self._required(
                        request.payload,
                        "version",
                    ),
                )

                return self._success(
                    request,
                    {
                        "model_version": item.to_dict(),
                    },
                )

            if operation == "promote_version":
                item = self.registry.promote(
                    self._required(
                        request.payload,
                        "model_id",
                    ),
                    self._required(
                        request.payload,
                        "version",
                    ),
                )

                return self._success(
                    request,
                    {
                        "model_version": item.to_dict(),
                    },
                )

            if operation == "deprecate_version":
                item = self.registry.deprecate(
                    self._required(
                        request.payload,
                        "model_id",
                    ),
                    self._required(
                        request.payload,
                        "version",
                    ),
                )

                return self._success(
                    request,
                    {
                        "model_version": item.to_dict(),
                    },
                )

            if operation == "active_version":
                item = self.registry.active(
                    self._required(
                        request.payload,
                        "model_id",
                    )
                )

                return self._success(
                    request,
                    {
                        "model_version": item.to_dict(),
                    },
                )

            if operation == "verify_version":
                result = self.registry.verify(
                    self._required(
                        request.payload,
                        "model_id",
                    ),
                    self._required(
                        request.payload,
                        "version",
                    ),
                )

                return self._success(
                    request,
                    {
                        "verification": result,
                    },
                )

            if operation == "discover_checkpoints":
                paths = self._required(
                    request.payload,
                    "paths",
                )

                results = (
                    self.registry
                    .inspector
                    .discover(
                        paths
                    )
                )

                return self._success(
                    request,
                    {
                        "checkpoints": results,
                        "count": len(
                            results
                        ),
                    },
                )

            if operation == "export_registry":
                return self._success(
                    request,
                    {
                        "state": (
                            self.registry
                            .export_state()
                        ),
                    },
                )

            if operation == "load_registry":
                self.registry.load_state(
                    self._required(
                        request.payload,
                        "state",
                    )
                )

                return self._success(
                    request,
                    {
                        "models": (
                            self.registry
                            .models()
                        ),
                    },
                )

            return self._error(
                request,
                "INVALID_REQUEST",
                "Unsupported model registry operation",
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
