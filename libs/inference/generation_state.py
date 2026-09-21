class GenerationState:
    """
    Mutable generation session state with explicit stop reason and counters.
    """

    def __init__(
        self,
        prompt_ids,
        max_new_tokens,
        eos_token_ids=None,
    ):
        if not isinstance(prompt_ids, (list, tuple)):
            raise TypeError("prompt_ids must be list or tuple")

        if len(prompt_ids) == 0:
            raise ValueError("prompt_ids must not be empty")

        for token_id in prompt_ids:
            if not isinstance(token_id, int):
                raise TypeError("prompt token IDs must be ints")

        if not isinstance(max_new_tokens, int) or max_new_tokens < 0:
            raise ValueError(
                "max_new_tokens must be non-negative int"
            )

        if eos_token_ids is None:
            eos_token_ids = []

        if isinstance(eos_token_ids, int):
            eos_token_ids = [eos_token_ids]

        self.prompt_ids = list(prompt_ids)
        self.generated_ids = []
        self.max_new_tokens = max_new_tokens
        self.eos_token_ids = list(eos_token_ids)

        for token_id in self.eos_token_ids:
            if not isinstance(token_id, int):
                raise TypeError("EOS token IDs must be ints")

        self.finished = False
        self.stop_reason = None

    def all_ids(self):
        return (
            list(self.prompt_ids)
            + list(self.generated_ids)
        )

    def new_token_count(self):
        return len(self.generated_ids)

    def append(self, token_id):
        if self.finished:
            raise RuntimeError(
                "cannot append after generation is finished"
            )

        if not isinstance(token_id, int):
            raise TypeError("generated token ID must be int")

        self.generated_ids.append(token_id)

        if token_id in self.eos_token_ids:
            self.finished = True
            self.stop_reason = "eos"

        elif len(self.generated_ids) >= self.max_new_tokens:
            self.finished = True
            self.stop_reason = "max_new_tokens"

        return self

    def finish(self, reason):
        if not isinstance(reason, str) or reason == "":
            raise ValueError("stop reason must be non-empty str")

        self.finished = True
        self.stop_reason = reason
        return self

    def to_dict(self):
        return {
            "prompt_ids": list(self.prompt_ids),
            "generated_ids": list(self.generated_ids),
            "max_new_tokens": self.max_new_tokens,
            "eos_token_ids": list(self.eos_token_ids),
            "finished": self.finished,
            "stop_reason": self.stop_reason,
        }
