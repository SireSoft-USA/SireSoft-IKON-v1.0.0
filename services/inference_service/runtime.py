class InferenceRuntime:
    """
    Owns the currently loaded checkpoint-backed LanguageModel and performs real
    autoregressive generation through libs/inference.

    The current core generator recomputes the retained context every token.
    KV-cache storage exists in libs/inference but is not yet wired into attention.
    """

    def __init__(
        self,
        loader,
    ):
        if loader is None or not hasattr(
            loader,
            "load_version",
        ):
            raise TypeError(
                "loader must provide load_version()"
            )

        self.loader = loader
        self.loaded = None

    def ready(
        self,
    ):
        return (
            self.loaded is not None
        )

    def status(
        self,
    ):
        if self.loaded is None:
            return {
                "ready": False,
                "model": None,
            }

        return {
            "ready": True,
            "model": (
                self.loaded.info()
            ),
        }

    def load_active(
        self,
        model_id,
    ):
        loaded = (
            self.loader
            .load_active(
                model_id
            )
        )

        self.loaded = loaded
        return loaded.info()

    def load_version(
        self,
        model_id,
        version,
    ):
        loaded = (
            self.loader
            .load_version(
                model_id,
                version,
            )
        )

        self.loaded = loaded
        return loaded.info()

    def sync_active(
        self,
        model_id=None,
    ):
        if model_id is None:
            if self.loaded is None:
                raise RuntimeError(
                    "no loaded model; model_id is required"
                )

            model_id = (
                self.loaded.model_id
            )

        active = (
            self.loader
            .registry
            .active(
                model_id
            )
        )

        if (
            self.loaded is not None
            and self.loaded.model_id
            == model_id
            and self.loaded.version
            == active.version
        ):
            return {
                "switched": False,
                "model": (
                    self.loaded.info()
                ),
            }

        info = self.load_version(
            model_id,
            active.version,
        )

        return {
            "switched": True,
            "model": info,
        }

    def unload(
        self,
    ):
        previous = (
            None
            if self.loaded is None
            else self.loaded.info()
        )

        self.loaded = None

        return {
            "unloaded": (
                previous is not None
            ),
            "previous_model": previous,
        }

    def generate(
        self,
        prompt_ids,
        max_new_tokens=32,
        eos_token_ids=None,
        sampler="greedy",
        seed=1337,
        temperature=1.0,
        top_k=None,
        top_p=None,
        repetition_penalty=1.0,
        banned_token_ids=None,
        allow_prompt_truncation=True,
    ):
        self._require_ready()

        prompt = self._validate_prompt(
            prompt_ids
        )

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
            self.loaded
            .model
            .max_seq_len
        )

        effective_prompt = list(
            prompt
        )

        if len(
            effective_prompt
        ) > context_window:
            if not allow_prompt_truncation:
                raise ValueError(
                    "prompt exceeds loaded model context window"
                )

            effective_prompt = (
                effective_prompt[
                    len(
                        effective_prompt
                    )
                    - context_window:
                ]
            )

        sampler_object = (
            self._sampler(
                sampler,
                seed,
            )
        )

        processor = LogitsProcessor(
            temperature=temperature,
            top_k=top_k,
            top_p=top_p,
            repetition_penalty=(
                repetition_penalty
            ),
            banned_token_ids=(
                []
                if banned_token_ids is None
                else banned_token_ids
            ),
        )

        generator = InferenceGenerator(
            model=self.loaded.model,
            sampler=sampler_object,
            logits_processor=processor,
            context_window=context_window,
        )

        state = generator.generate(
            prompt_ids=effective_prompt,
            max_new_tokens=max_new_tokens,
            eos_token_ids=eos_token_ids,
        )

        return InferenceResult(
            model_id=self.loaded.model_id,
            version=self.loaded.version,
            prompt_ids=prompt,
            effective_prompt_ids=(
                effective_prompt
            ),
            generated_ids=(
                state.generated_ids
            ),
            stop_reason=(
                state.stop_reason
            ),
            sampler=str(
                sampler
            ).lower(),
            context_window=context_window,
        )

    def _sampler(
        self,
        sampler,
        seed,
    ):
        kind = str(
            sampler
        ).lower()

        if kind == "greedy":
            return GreedySampler()

        if kind in (
            "categorical",
            "sample",
        ):
            if not isinstance(seed, int):
                raise TypeError(
                    "sampling seed must be int"
                )

            return CategoricalSampler(
                seed=seed
            )

        raise ValueError(
            "unsupported sampler: "
            + kind
        )

    def _validate_prompt(
        self,
        prompt_ids,
    ):
        if not isinstance(
            prompt_ids,
            (list, tuple),
        ):
            raise TypeError(
                "prompt_ids must be list/tuple"
            )

        if len(prompt_ids) == 0:
            raise ValueError(
                "prompt_ids must not be empty"
            )

        vocab_size = (
            self.loaded
            .model
            .vocab_size
        )

        result = []

        for token_id in prompt_ids:
            if not isinstance(
                token_id,
                int,
            ):
                raise TypeError(
                    "prompt token IDs must be ints"
                )

            if (
                token_id < 0
                or token_id
                >= vocab_size
            ):
                raise ValueError(
                    "prompt token ID outside loaded vocabulary"
                )

            result.append(
                token_id
            )

        return result

    def _require_ready(
        self,
    ):
        if self.loaded is None:
            raise RuntimeError(
                "no model is loaded for inference"
            )
