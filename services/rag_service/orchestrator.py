class RAGServiceOrchestrator:
    """
    End-to-end chatbot orchestration:

      input guard
      -> retrieval_service vector space/index
      -> ranking + whole-chunk context budgeting
      -> retrieved-context guard/quarantine
      -> deterministic RAG prompt
      -> inference_service runtime
      -> output guard
      -> citations + redacted safety metadata

    Retrieved chunks are never truncated mid-evidence to fit the model prompt.
    """

    def __init__(
        self,
        tokenizer,
        retrieval_manager,
        inference_runtime,
        safety_engine=None,
        max_context_tokens=512,
        prompt_builder=None,
    ):
        if tokenizer is None or not hasattr(
            tokenizer,
            "encode",
        ):
            raise TypeError(
                "tokenizer must provide encode()"
            )

        if not hasattr(
            tokenizer,
            "decode",
        ):
            raise TypeError(
                "tokenizer must provide decode()"
            )

        if inference_runtime is None or not hasattr(
            inference_runtime,
            "generate",
        ):
            raise TypeError(
                "inference_runtime must provide generate()"
            )

        self.tokenizer = tokenizer

        self.retrieval_bridge = (
            RAGRetrievalBridge(
                retrieval_manager
            )
        )

        self.retrieval_manager = (
            retrieval_manager
        )

        self.inference_runtime = (
            inference_runtime
        )

        self.safety_engine = (
            GuardrailEngine()
            if safety_engine is None
            else safety_engine
        )

        self.safety_view = (
            PublicSafetyView()
        )

        self.context_builder = (
            ContextBuilder(
                tokenizer=tokenizer,
                max_context_tokens=(
                    max_context_tokens
                ),
            )
        )

        self.prompt_builder = (
            PromptBuilder(
                compact=True
            )
            if prompt_builder is None
            else prompt_builder
        )

    def prepare(
        self,
        query_text,
        candidate_k=20,
        top_k=5,
        min_score=None,
        filters=None,
        use_mmr=True,
        mmr_lambda=0.75,
        similarity_weight=1.0,
        dataset_boosts=None,
        document_boosts=None,
        metadata_boosts=None,
        max_prompt_tokens=None,
        max_new_tokens=64,
    ):
        input_decision = (
            self.safety_engine
            .check_input(
                query_text,
                metadata={
                    "operation": (
                        "rag_prepare"
                    ),
                },
            )
        )

        if not input_decision.allowed():
            return RAGPreparation(
                query_text=query_text,
                status="blocked",
                blocked_phase="input",
                retrieval=None,
                context=None,
                prompt="",
                prompt_ids=[],
                input_decision=(
                    input_decision
                ),
                context_decision=None,
                safety_view=(
                    self.safety_view
                ),
            )

        retrieval = (
            self.retrieval_bridge
            .retrieve(
                query_text=query_text,
                candidate_k=candidate_k,
                top_k=top_k,
                min_score=min_score,
                filters=filters,
                use_mmr=use_mmr,
                mmr_lambda=mmr_lambda,
                similarity_weight=(
                    similarity_weight
                ),
                dataset_boosts=(
                    dataset_boosts
                ),
                document_boosts=(
                    document_boosts
                ),
                metadata_boosts=(
                    metadata_boosts
                ),
            )
        )

        if max_prompt_tokens is None:
            max_prompt_tokens = (
                self._available_prompt_tokens(
                    max_new_tokens
                )
            )

        if max_prompt_tokens is not None:
            if (
                not isinstance(
                    max_prompt_tokens,
                    int,
                )
                or max_prompt_tokens <= 0
            ):
                raise ValueError(
                    "max_prompt_tokens must be positive int or None"
                )

        active_results = list(
            retrieval.ranked_results
        )

        final_context = None
        final_context_decision = None
        final_prompt = ""
        final_prompt_ids = []

        while True:
            context = (
                self.context_builder
                .build(
                    active_results
                )
            )

            context_decision = (
                self.safety_engine
                .check_context(
                    context.text,
                    metadata={
                        "operation": (
                            "rag_prepare"
                        ),
                        "source_count": (
                            context
                            .source_count()
                        ),
                    },
                )
            )

            if not context_decision.allowed():
                return RAGPreparation(
                    query_text=query_text,
                    status="blocked",
                    blocked_phase="context",
                    retrieval=retrieval,
                    context=None,
                    prompt="",
                    prompt_ids=[],
                    input_decision=(
                        input_decision
                    ),
                    context_decision=(
                        context_decision
                    ),
                    safety_view=(
                        self.safety_view
                    ),
                )

            safe_context_text = (
                context_decision
                .safe_text
            )

            if safe_context_text is None:
                safe_context_text = ""

            safe_context = (
                ContextPackage(
                    text=(
                        safe_context_text
                    ),
                    citations=(
                        context.citations
                    ),
                    token_count=len(
                        self.tokenizer
                        .encode(
                            safe_context_text
                        )
                    ),
                    skipped_item_ids=(
                        context
                        .skipped_item_ids
                    ),
                )
            )

            prompt = (
                self.prompt_builder
                .build(
                    query_text,
                    safe_context,
                )
            )

            prompt_ids = (
                self.tokenizer
                .encode(
                    prompt
                )
            )

            final_context = (
                safe_context
            )

            final_context_decision = (
                context_decision
            )

            final_prompt = prompt
            final_prompt_ids = (
                prompt_ids
            )

            if (
                max_prompt_tokens is None
                or len(
                    prompt_ids
                )
                <= max_prompt_tokens
            ):
                break

            if len(
                active_results
            ) == 0:
                raise ValueError(
                    "base RAG prompt exceeds available model prompt capacity"
                )

            active_results = (
                active_results[
                    :-1
                ]
            )

        prepared_retrieval = (
            RetrievalBundle(
                query_text=(
                    retrieval.query_text
                ),
                query_embedding=(
                    retrieval
                    .query_embedding
                ),
                raw_results=(
                    retrieval.raw_results
                ),
                ranked_results=(
                    active_results
                ),
            )
        )

        return RAGPreparation(
            query_text=query_text,
            status="ready",
            blocked_phase=None,
            retrieval=(
                prepared_retrieval
            ),
            context=(
                final_context
            ),
            prompt=(
                final_prompt
            ),
            prompt_ids=(
                final_prompt_ids
            ),
            input_decision=(
                input_decision
            ),
            context_decision=(
                final_context_decision
            ),
            safety_view=(
                self.safety_view
            ),
        )

    def answer(
        self,
        query_text,
        max_new_tokens=64,
        candidate_k=20,
        top_k=5,
        min_score=None,
        filters=None,
        use_mmr=True,
        mmr_lambda=0.75,
        similarity_weight=1.0,
        dataset_boosts=None,
        document_boosts=None,
        metadata_boosts=None,
        eos_token_ids=None,
        sampler="greedy",
        seed=1337,
        temperature=1.0,
        top_k_sampling=None,
        top_p=None,
        repetition_penalty=1.0,
        banned_token_ids=None,
    ):
        if not self.inference_runtime.ready():
            raise RuntimeError(
                "RAG generation requires a loaded inference model"
            )

        preparation = self.prepare(
            query_text=query_text,
            candidate_k=candidate_k,
            top_k=top_k,
            min_score=min_score,
            filters=filters,
            use_mmr=use_mmr,
            mmr_lambda=mmr_lambda,
            similarity_weight=(
                similarity_weight
            ),
            dataset_boosts=(
                dataset_boosts
            ),
            document_boosts=(
                document_boosts
            ),
            metadata_boosts=(
                metadata_boosts
            ),
            max_prompt_tokens=None,
            max_new_tokens=(
                max_new_tokens
            ),
        )

        if not preparation.ready():
            return RAGServiceResult(
                preparation=preparation,
                answer_text="",
                generated_ids=[],
                generated_count=0,
                stop_reason=(
                    "guardrail_"
                    + str(
                        preparation
                        .blocked_phase
                    )
                    + "_block"
                ),
                output_decision=None,
                safety_view=(
                    self.safety_view
                ),
                status="blocked",
                blocked_phase=(
                    preparation
                    .blocked_phase
                ),
            )

        generation = (
            self.inference_runtime
            .generate(
                prompt_ids=(
                    preparation
                    .prompt_ids
                ),
                max_new_tokens=(
                    max_new_tokens
                ),
                eos_token_ids=(
                    eos_token_ids
                ),
                sampler=sampler,
                seed=seed,
                temperature=(
                    temperature
                ),
                top_k=(
                    top_k_sampling
                ),
                top_p=top_p,
                repetition_penalty=(
                    repetition_penalty
                ),
                banned_token_ids=(
                    banned_token_ids
                ),
                allow_prompt_truncation=False,
            )
        )

        raw_answer = (
            self._safe_decode(
                generation
                .generated_ids
            )
        )

        output_decision = (
            self.safety_engine
            .check_output(
                raw_answer,
                metadata={
                    "operation": (
                        "rag_answer"
                    ),
                    "generated_count": (
                        len(
                            generation
                            .generated_ids
                        )
                    ),
                },
            )
        )

        if not output_decision.allowed():
            return RAGServiceResult(
                preparation=(
                    preparation
                ),
                answer_text="",
                generated_ids=[],
                generated_count=len(
                    generation
                    .generated_ids
                ),
                stop_reason=(
                    "guardrail_output_block"
                ),
                output_decision=(
                    output_decision
                ),
                safety_view=(
                    self.safety_view
                ),
                status="blocked",
                blocked_phase="output",
            )

        answer_text = (
            output_decision
            .safe_text
        )

        if answer_text is None:
            answer_text = ""

        return RAGServiceResult(
            preparation=(
                preparation
            ),
            answer_text=(
                answer_text
            ),
            generated_ids=(
                generation
                .generated_ids
            ),
            generated_count=len(
                generation
                .generated_ids
            ),
            stop_reason=(
                generation
                .stop_reason
            ),
            output_decision=(
                output_decision
            ),
            safety_view=(
                self.safety_view
            ),
            status="ok",
            blocked_phase=None,
        )

    def status(
        self,
    ):
        inference = (
            self.inference_runtime
            .status()
        )

        return {
            "ready": bool(
                inference.get(
                    "ready",
                    False,
                )
            ),
            "retrieval": (
                self.retrieval_manager
                .status()
            ),
            "inference": inference,
            "safety_audit_records": len(
                self.safety_engine
                .audit_records()
            ),
            "max_context_tokens": (
                self.context_builder
                .max_context_tokens
            ),
        }

    def audit_summary(
        self,
    ):
        return (
            self.safety_view
            .audit_records(
                self.safety_engine
                .audit_records()
            )
        )

    def clear_audit(
        self,
    ):
        self.safety_engine.clear_audit()

        return {
            "cleared": True,
            "remaining": 0,
        }

    def _available_prompt_tokens(
        self,
        max_new_tokens,
    ):
        if not self.inference_runtime.ready():
            return None

        if (
            not isinstance(
                max_new_tokens,
                int,
            )
            or max_new_tokens < 0
        ):
            raise ValueError(
                "max_new_tokens must be non-negative int"
            )

        context_window = (
            self.inference_runtime
            .loaded
            .model
            .max_seq_len
        )

        available = (
            context_window
            - max_new_tokens
        )

        if available <= 0:
            raise ValueError(
                "generation request leaves no prompt capacity"
            )

        return available

    def _safe_decode(
        self,
        token_ids,
    ):
        end = len(
            token_ids
        )

        while end >= 0:
            try:
                return (
                    self.tokenizer
                    .decode(
                        token_ids[
                            :end
                        ],
                        skip_special=True,
                    )
                )

            except ValueError:
                end -= 1

        return ""
