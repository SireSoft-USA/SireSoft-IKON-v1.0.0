class RetrievalService:
    """
    Protocol-facing searchable retrieval service.

    Supported operations:
      index_documents
      upsert_documents
      remove_document
      search
      status
      save_state
      load_state
      clear
    """

    def __init__(
        self,
        manager,
    ):
        if manager is None or not hasattr(
            manager,
            "search",
        ):
            raise TypeError(
                "manager must provide retrieval operations"
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

        if request.service != "retrieval_service":
            return self._error(
                request,
                "INVALID_REQUEST",
                "Request targeted the wrong service",
            )

        try:
            operation = (
                request.operation
            )

            if operation in (
                "index_documents",
                "upsert_documents",
            ):
                mode = (
                    "replace"
                    if operation
                    == "index_documents"
                    else "upsert"
                )

                status = (
                    self.manager
                    .index_documents(
                        self._required(
                            request.payload,
                            "documents",
                        ),
                        mode=mode,
                        refit=request.payload.get(
                            "refit",
                            True,
                        ),
                    )
                )

                return self._success(
                    request,
                    {
                        "status": status,
                    },
                )

            if operation == "remove_document":
                status = (
                    self.manager
                    .remove_document(
                        self._required(
                            request.payload,
                            "document_id",
                        ),
                        refit=request.payload.get(
                            "refit",
                            True,
                        ),
                    )
                )

                return self._success(
                    request,
                    {
                        "status": status,
                    },
                )

            if operation == "search":
                result = (
                    self.manager
                    .search(
                        query=self._required(
                            request.payload,
                            "query",
                        ),
                        top_k=request.payload.get(
                            "top_k",
                            5,
                        ),
                        search_k=request.payload.get(
                            "search_k"
                        ),
                        min_score=request.payload.get(
                            "min_score"
                        ),
                        filters=request.payload.get(
                            "filters"
                        ),
                        use_mmr=request.payload.get(
                            "use_mmr",
                            True,
                        ),
                        mmr_lambda=request.payload.get(
                            "mmr_lambda",
                            0.75,
                        ),
                        similarity_weight=request.payload.get(
                            "similarity_weight",
                            1.0,
                        ),
                        dataset_boosts=request.payload.get(
                            "dataset_boosts"
                        ),
                        document_boosts=request.payload.get(
                            "document_boosts"
                        ),
                        metadata_boosts=request.payload.get(
                            "metadata_boosts"
                        ),
                    )
                )

                return self._success(
                    request,
                    {
                        "result": (
                            result.to_dict()
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

            if operation == "clear":
                return self._success(
                    request,
                    {
                        "status": (
                            self.manager
                            .clear()
                        ),
                    },
                )

            return self._error(
                request,
                "INVALID_REQUEST",
                "Unsupported retrieval service operation",
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


def build_retrieval_manager(
    tokenizer,
    dimension=256,
    max_chars=1200,
    overlap_chars=150,
):
    return RetrievalManager(
        tokenizer=tokenizer,
        Document=Document,
        dimension=dimension,
        max_chars=max_chars,
        overlap_chars=overlap_chars,
    )
