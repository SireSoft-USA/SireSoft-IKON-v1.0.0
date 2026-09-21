class EmbeddingService:
    """
    Protocol-facing retrieval embedding service.

    Supported operations:
      configure
      fit
      info
      embed_text
      embed_tokens
      embed_many
      export_state
      load_state
      save_state_file
      load_state_file
    """

    def __init__(
        self,
        manager,
    ):
        if manager is None or not hasattr(
            manager,
            "embed_text",
        ):
            raise TypeError(
                "manager must provide embedding operations"
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

        if request.service != "embedding_service":
            return self._error(
                request,
                "INVALID_REQUEST",
                "Request targeted the wrong service",
            )

        try:
            operation = (
                request.operation
            )

            if operation == "configure":
                info = (
                    self.manager
                    .configure(
                        dimension=request.payload.get(
                            "dimension",
                            256,
                        ),
                        min_n=request.payload.get(
                            "min_n",
                            1,
                        ),
                        max_n=request.payload.get(
                            "max_n",
                            2,
                        ),
                        use_idf=request.payload.get(
                            "use_idf",
                            True,
                        ),
                        sublinear_tf=request.payload.get(
                            "sublinear_tf",
                            True,
                        ),
                        l2_normalize=request.payload.get(
                            "l2_normalize",
                            True,
                        ),
                    )
                )

                return self._success(
                    request,
                    {
                        "info": info,
                    },
                )

            if operation == "fit":
                info = self.manager.fit(
                    self._required(
                        request.payload,
                        "texts",
                    )
                )

                return self._success(
                    request,
                    {
                        "info": info,
                    },
                )

            if operation == "info":
                return self._success(
                    request,
                    {
                        "info": (
                            self.manager
                            .info()
                        ),
                    },
                )

            if operation == "embed_text":
                result = (
                    self.manager
                    .embed_text(
                        self._required(
                            request.payload,
                            "text",
                        )
                    )
                )

                return self._success(
                    request,
                    {
                        "embedding": (
                            result.to_dict()
                        ),
                    },
                )

            if operation == "embed_tokens":
                result = (
                    self.manager
                    .embed_tokens(
                        self._required(
                            request.payload,
                            "token_ids",
                        )
                    )
                )

                return self._success(
                    request,
                    {
                        "embedding": (
                            result.to_dict()
                        ),
                    },
                )

            if operation == "embed_many":
                results = (
                    self.manager
                    .embed_many(
                        self._required(
                            request.payload,
                            "texts",
                        )
                    )
                )

                return self._success(
                    request,
                    {
                        "embeddings": [
                            result.to_dict()
                            for result
                            in results
                        ],
                        "count": len(
                            results
                        ),
                    },
                )

            if operation == "export_state":
                return self._success(
                    request,
                    {
                        "state": (
                            self.manager
                            .export_state()
                        ),
                    },
                )

            if operation == "load_state":
                info = (
                    self.manager
                    .load_state(
                        self._required(
                            request.payload,
                            "state",
                        ),
                        expected_dimension=request.payload.get(
                            "expected_dimension"
                        ),
                    )
                )

                return self._success(
                    request,
                    {
                        "info": info,
                    },
                )

            if operation == "save_state_file":
                info = (
                    self.manager
                    .save_state_file(
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

            if operation == "load_state_file":
                info = (
                    self.manager
                    .load_state_file(
                        self._required(
                            request.payload,
                            "path",
                        ),
                        expected_dimension=request.payload.get(
                            "expected_dimension"
                        ),
                    )
                )

                return self._success(
                    request,
                    {
                        "info": info,
                    },
                )

            return self._error(
                request,
                "INVALID_REQUEST",
                "Unsupported embedding service operation",
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
            KeyError,
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


def build_embedding_manager(
    tokenizer,
    dimension=256,
    min_n=1,
    max_n=2,
):
    return EmbeddingManager(
        tokenizer=tokenizer,
        dimension=dimension,
        min_n=min_n,
        max_n=max_n,
    )
