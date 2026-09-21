class InferenceGenerator:
    """
    Production-style generation orchestration for the current SireLLM model.

    The current Transformer computes a full forward pass over the retained
    context on each step. KVCache storage is implemented separately and will be
    wired into attention in a later optimization stage.
    """

    def __init__(
        self,
        model,
        sampler=None,
        logits_processor=None,
        context_window=None,
    ):
        if model is None or not hasattr(model, "forward"):
            raise TypeError("model must provide forward()")

        if sampler is None:
            sampler = GreedySampler()

        if not hasattr(sampler, "sample"):
            raise TypeError("sampler must provide sample(logits)")

        if logits_processor is None:
            logits_processor = LogitsProcessor()

        if not hasattr(
            logits_processor,
            "process",
        ):
            raise TypeError(
                "logits_processor must provide process()"
            )

        if context_window is None:
            context_window = getattr(
                model,
                "max_seq_len",
                None,
            )

        if context_window is not None:
            if (
                not isinstance(context_window, int)
                or context_window <= 0
            ):
                raise ValueError(
                    "context_window must be positive int or None"
                )

        self.model = model
        self.sampler = sampler
        self.logits_processor = (
            logits_processor
        )
        self.context_window = (
            context_window
        )

    def generate(
        self,
        prompt_ids,
        max_new_tokens,
        eos_token_ids=None,
    ):
        state = GenerationState(
            prompt_ids=prompt_ids,
            max_new_tokens=max_new_tokens,
            eos_token_ids=eos_token_ids,
        )

        if max_new_tokens == 0:
            state.finish(
                "max_new_tokens"
            )
            return state

        was_training = bool(
            getattr(
                self.model,
                "training",
                True,
            )
        )

        self.model.eval()

        try:
            while not state.finished:
                complete_history = (
                    state.all_ids()
                )

                model_input = (
                    self._context_slice(
                        complete_history
                    )
                )

                logits = self.model(
                    [model_input]
                )

                last_logits = (
                    self._last_logits(
                        logits,
                        len(model_input),
                    )
                )

                processed = (
                    self.logits_processor.process(
                        last_logits,
                        token_history=complete_history,
                    )
                )

                next_token = (
                    self.sampler.sample(
                        processed
                    )
                )

                state.append(
                    next_token
                )

        finally:
            if was_training:
                self.model.train()

        return state

    def _context_slice(self, token_ids):
        if self.context_window is None:
            return list(token_ids)

        if len(token_ids) <= self.context_window:
            return list(token_ids)

        return list(
            token_ids[
                len(token_ids)
                - self.context_window:
            ]
        )

    def _last_logits(
        self,
        logits,
        sequence_length,
    ):
        if logits.ndim == 3:
            vocab_size = logits.shape[2]
            values = logits.data.flatten()

            start = (
                (sequence_length - 1)
                * vocab_size
            )

            return values[
                start:start + vocab_size
            ]

        if logits.ndim == 2:
            vocab_size = logits.shape[1]
            values = logits.data.flatten()

            start = (
                (sequence_length - 1)
                * vocab_size
            )

            return values[
                start:start + vocab_size
            ]

        raise ValueError(
            "language model logits must be rank 2 or 3"
        )
