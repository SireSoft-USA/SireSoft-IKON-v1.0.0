class RAGGenerationConfig:
    def __init__(
        self,
        max_new_tokens=64,
        eos_token_ids=None,
        sampler="greedy",
        seed=1337,
        temperature=1.0,
        top_k_sampling=None,
        top_p=None,
        repetition_penalty=1.0,
        banned_token_ids=None,
    ):
        if (
            not isinstance(max_new_tokens, int)
            or max_new_tokens < 0
        ):
            raise ValueError(
                "max_new_tokens must be non-negative int"
            )

        sampler = str(sampler).lower()

        if sampler not in (
            "greedy",
            "categorical",
            "sample",
        ):
            raise ValueError(
                "unsupported sampler"
            )

        if not isinstance(seed, int):
            raise TypeError(
                "seed must be int"
            )

        if (
            not isinstance(
                temperature,
                (int, float),
            )
            or temperature <= 0.0
        ):
            raise ValueError(
                "temperature must be > 0"
            )

        if top_k_sampling is not None and (
            not isinstance(
                top_k_sampling,
                int,
            )
            or top_k_sampling <= 0
        ):
            raise ValueError(
                "top_k_sampling must be positive int or None"
            )

        if top_p is not None:
            if not isinstance(
                top_p,
                (int, float),
            ):
                raise TypeError(
                    "top_p must be numeric or None"
                )

            if (
                top_p <= 0.0
                or top_p > 1.0
            ):
                raise ValueError(
                    "top_p must satisfy 0 < value <= 1"
                )

        if (
            not isinstance(
                repetition_penalty,
                (int, float),
            )
            or repetition_penalty < 1.0
        ):
            raise ValueError(
                "repetition_penalty must be >= 1"
            )

        if eos_token_ids is None:
            eos_token_ids = []

        if banned_token_ids is None:
            banned_token_ids = []

        self.max_new_tokens = (
            max_new_tokens
        )
        self.eos_token_ids = self._token_ids(
            eos_token_ids,
            "eos_token_ids",
        )
        self.sampler = sampler
        self.seed = seed
        self.temperature = float(
            temperature
        )
        self.top_k_sampling = (
            top_k_sampling
        )
        self.top_p = (
            None
            if top_p is None
            else float(top_p)
        )
        self.repetition_penalty = float(
            repetition_penalty
        )
        self.banned_token_ids = self._token_ids(
            banned_token_ids,
            "banned_token_ids",
        )

    def to_dict(self):
        return {
            "max_new_tokens": self.max_new_tokens,
            "eos_token_ids": list(
                self.eos_token_ids
            ),
            "sampler": self.sampler,
            "seed": self.seed,
            "temperature": self.temperature,
            "top_k_sampling": (
                self.top_k_sampling
            ),
            "top_p": self.top_p,
            "repetition_penalty": (
                self.repetition_penalty
            ),
            "banned_token_ids": list(
                self.banned_token_ids
            ),
        }

    def _token_ids(
        self,
        values,
        field_name,
    ):
        if not isinstance(
            values,
            (list, tuple),
        ):
            raise TypeError(
                field_name
                + " must be list/tuple"
            )

        result = []
        seen = {}

        for token_id in values:
            if (
                not isinstance(token_id, int)
                or token_id < 0
            ):
                raise ValueError(
                    field_name
                    + " must contain non-negative ints"
                )

            if token_id not in seen:
                seen[token_id] = True
                result.append(token_id)

        return result
