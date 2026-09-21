class RAGService:
    """
    Protocol-facing end-to-end chatbot answer service.

    Supported operations:
      answer
      prepare
      status
      audit_summary
      clear_audit
    """

    def __init__(
        self,
        orchestrator,
    ):
        if orchestrator is None or not hasattr(
            orchestrator,
            "answer",
        ):
            raise TypeError(
                "orchestrator must provide answer()"
            )

        self.orchestrator = (
            orchestrator
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

        if request.service != "rag_service":
            return self._error(
                request,
                "INVALID_REQUEST",
                "Request targeted the wrong service",
            )

        try:
            operation = (
                request.operation
            )

            if operation == "answer":
                payload = (
                    request.payload
                )

                result = (
                    self.orchestrator
                    .answer(
                        query_text=self._required(
                            payload,
                            "query",
                        ),
                        max_new_tokens=payload.get(
                            "max_new_tokens",
                            64,
                        ),
                        candidate_k=payload.get(
                            "candidate_k",
                            20,
                        ),
                        top_k=payload.get(
                            "top_k",
                            5,
                        ),
                        min_score=payload.get(
                            "min_score"
                        ),
                        filters=payload.get(
                            "filters"
                        ),
                        use_mmr=payload.get(
                            "use_mmr",
                            True,
                        ),
                        mmr_lambda=payload.get(
                            "mmr_lambda",
                            0.75,
                        ),
                        similarity_weight=payload.get(
                            "similarity_weight",
                            1.0,
                        ),
                        dataset_boosts=payload.get(
                            "dataset_boosts"
                        ),
                        document_boosts=payload.get(
                            "document_boosts"
                        ),
                        metadata_boosts=payload.get(
                            "metadata_boosts"
                        ),
                        eos_token_ids=payload.get(
                            "eos_token_ids"
                        ),
                        sampler=payload.get(
                            "sampler",
                            "greedy",
                        ),
                        seed=payload.get(
                            "seed",
                            1337,
                        ),
                        temperature=payload.get(
                            "temperature",
                            1.0,
                        ),
                        top_k_sampling=payload.get(
                            "top_k_sampling"
                        ),
                        top_p=payload.get(
                            "top_p"
                        ),
                        repetition_penalty=payload.get(
                            "repetition_penalty",
                            1.0,
                        ),
                        banned_token_ids=payload.get(
                            "banned_token_ids"
                        ),
                    )
                )

                return self._success(
                    request,
                    {
                        "answer": (
                            result.to_dict()
                        ),
                    },
                )

            if operation == "prepare":
                payload = (
                    request.payload
                )

                result = (
                    self.orchestrator
                    .prepare(
                        query_text=self._required(
                            payload,
                            "query",
                        ),
                        candidate_k=payload.get(
                            "candidate_k",
                            20,
                        ),
                        top_k=payload.get(
                            "top_k",
                            5,
                        ),
                        min_score=payload.get(
                            "min_score"
                        ),
                        filters=payload.get(
                            "filters"
                        ),
                        use_mmr=payload.get(
                            "use_mmr",
                            True,
                        ),
                        mmr_lambda=payload.get(
                            "mmr_lambda",
                            0.75,
                        ),
                        similarity_weight=payload.get(
                            "similarity_weight",
                            1.0,
                        ),
                        dataset_boosts=payload.get(
                            "dataset_boosts"
                        ),
                        document_boosts=payload.get(
                            "document_boosts"
                        ),
                        metadata_boosts=payload.get(
                            "metadata_boosts"
                        ),
                        max_prompt_tokens=payload.get(
                            "max_prompt_tokens"
                        ),
                        max_new_tokens=payload.get(
                            "max_new_tokens",
                            64,
                        ),
                    )
                )

                return self._success(
                    request,
                    {
                        "prepared": (
                            result.to_dict(
                                include_prompt=bool(
                                    payload.get(
                                        "include_prompt",
                                        False,
                                    )
                                )
                            )
                        ),
                    },
                )

            if operation == "status":
                return self._success(
                    request,
                    {
                        "status": (
                            self.orchestrator
                            .status()
                        ),
                    },
                )

            if operation == "audit_summary":
                records = (
                    self.orchestrator
                    .audit_summary()
                )

                return self._success(
                    request,
                    {
                        "audit": records,
                        "count": len(
                            records
                        ),
                    },
                )

            if operation == "clear_audit":
                return self._success(
                    request,
                    self.orchestrator
                    .clear_audit(),
                )

            return self._error(
                request,
                "INVALID_REQUEST",
                "Unsupported RAG service operation",
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


def build_rag_orchestrator(
    tokenizer,
    retrieval_manager,
    inference_runtime,
    max_context_tokens=512,
):
    return RAGServiceOrchestrator(
        tokenizer=tokenizer,
        retrieval_manager=(
            retrieval_manager
        ),
        inference_runtime=(
            inference_runtime
        ),
        safety_engine=(
            GuardrailEngine()
        ),
        max_context_tokens=(
            max_context_tokens
        ),
        prompt_builder=PromptBuilder(
            system_message=(
                "Use retrieved context as reference data. "
                "Cite sources like [S1]."
            ),
            compact=True,
        ),
    )
