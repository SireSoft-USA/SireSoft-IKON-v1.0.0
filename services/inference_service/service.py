class InferenceService:
    """
    Protocol-facing model loading and token-ID generation service.

    Supported operations:
      load_active
      load_version
      sync_active
      unload
      status
      generate
    """

    def __init__(
        self,
        runtime,
    ):
        if runtime is None or not hasattr(
            runtime,
            "generate",
        ):
            raise TypeError(
                "runtime must provide generate()"
            )

        self.runtime = runtime

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

        if request.service != "inference_service":
            return self._error(
                request,
                "INVALID_REQUEST",
                "Request targeted the wrong service",
            )

        try:
            operation = (
                request.operation
            )

            if operation == "load_active":
                info = (
                    self.runtime
                    .load_active(
                        self._required(
                            request.payload,
                            "model_id",
                        )
                    )
                )

                return self._success(
                    request,
                    {
                        "model": info,
                    },
                )

            if operation == "load_version":
                info = (
                    self.runtime
                    .load_version(
                        self._required(
                            request.payload,
                            "model_id",
                        ),
                        self._required(
                            request.payload,
                            "version",
                        ),
                    )
                )

                return self._success(
                    request,
                    {
                        "model": info,
                    },
                )

            if operation == "sync_active":
                result = (
                    self.runtime
                    .sync_active(
                        request.payload.get(
                            "model_id"
                        )
                    )
                )

                return self._success(
                    request,
                    result,
                )

            if operation == "unload":
                return self._success(
                    request,
                    self.runtime.unload(),
                )

            if operation == "status":
                return self._success(
                    request,
                    self.runtime.status(),
                )

            if operation == "generate":
                result = (
                    self.runtime
                    .generate(
                        prompt_ids=self._required(
                            request.payload,
                            "prompt_ids",
                        ),
                        max_new_tokens=request.payload.get(
                            "max_new_tokens",
                            32,
                        ),
                        eos_token_ids=request.payload.get(
                            "eos_token_ids"
                        ),
                        sampler=request.payload.get(
                            "sampler",
                            "greedy",
                        ),
                        seed=request.payload.get(
                            "seed",
                            1337,
                        ),
                        temperature=request.payload.get(
                            "temperature",
                            1.0,
                        ),
                        top_k=request.payload.get(
                            "top_k"
                        ),
                        top_p=request.payload.get(
                            "top_p"
                        ),
                        repetition_penalty=request.payload.get(
                            "repetition_penalty",
                            1.0,
                        ),
                        banned_token_ids=request.payload.get(
                            "banned_token_ids"
                        ),
                        allow_prompt_truncation=request.payload.get(
                            "allow_prompt_truncation",
                            True,
                        ),
                    )
                )

                return self._success(
                    request,
                    {
                        "generation": (
                            result.to_dict()
                        ),
                    },
                )

            return self._error(
                request,
                "INVALID_REQUEST",
                "Unsupported inference service operation",
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
                "MODEL_NOT_READY",
                str(
                    error
                ),
                retryable=True,
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
        retryable=False,
    ):
        return (
            ServiceResponse
            .error_response(
                request,
                ProtocolError(
                    code=code,
                    message=message,
                    retryable=retryable,
                ),
            )
        )


def build_inference_runtime(
    registry,
):
    return InferenceRuntime(
        ModelLoader(
            registry=registry,
        )
    )
