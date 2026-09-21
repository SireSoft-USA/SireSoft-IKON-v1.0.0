class InferenceResult:
    """
    Protocol-safe generation result.
    """

    def __init__(
        self,
        model_id,
        version,
        prompt_ids,
        effective_prompt_ids,
        generated_ids,
        stop_reason,
        sampler,
        context_window,
    ):
        self.model_id = model_id
        self.version = version
        self.prompt_ids = list(
            prompt_ids
        )
        self.effective_prompt_ids = list(
            effective_prompt_ids
        )
        self.generated_ids = list(
            generated_ids
        )
        self.stop_reason = stop_reason
        self.sampler = sampler
        self.context_window = (
            context_window
        )

    def prompt_truncated(
        self,
    ):
        return (
            len(
                self.effective_prompt_ids
            )
            < len(
                self.prompt_ids
            )
        )

    def to_dict(
        self,
    ):
        return {
            "model_id": self.model_id,
            "version": self.version,
            "prompt_ids": list(
                self.prompt_ids
            ),
            "effective_prompt_ids": list(
                self.effective_prompt_ids
            ),
            "prompt_truncated": (
                self.prompt_truncated()
            ),
            "generated_ids": list(
                self.generated_ids
            ),
            "generated_count": len(
                self.generated_ids
            ),
            "stop_reason": self.stop_reason,
            "sampler": self.sampler,
            "context_window": (
                self.context_window
            ),
        }
