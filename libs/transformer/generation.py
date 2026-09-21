class GreedyGenerator:
    """
    Basic autoregressive generation used to validate the language model.

    Sampling strategies, KV caching and production decoding belong to the later
    libs/inference folder. This class deliberately stays small.
    """

    def __init__(self, model):
        if model is None or not hasattr(model, "forward"):
            raise TypeError("model must provide forward()")
        self.model = model

    def generate(
        self,
        input_ids,
        max_new_tokens,
        eos_token_id=None,
    ):
        if not isinstance(input_ids, list):
            raise TypeError("input_ids must be list")
        if len(input_ids) == 0:
            raise ValueError("input_ids must not be empty")
        if not isinstance(max_new_tokens, int) or max_new_tokens < 0:
            raise ValueError(
                "max_new_tokens must be non-negative int"
            )

        tokens = list(input_ids)
        was_training = self.model.training
        self.model.eval()

        step = 0

        while step < max_new_tokens:
            logits = self.model([tokens])
            next_token = self._argmax_last(
                logits,
                len(tokens),
                self.model.vocab_size,
            )

            tokens.append(next_token)

            if (
                eos_token_id is not None
                and next_token == eos_token_id
            ):
                break

            step += 1

        if was_training:
            self.model.train()

        return tokens

    def _argmax_last(
        self,
        logits,
        sequence_length,
        vocab_size,
    ):
        if logits.ndim == 3:
            values = logits.data.flatten()
            start = (
                (sequence_length - 1)
                * vocab_size
            )
        elif logits.ndim == 2:
            values = logits.data.flatten()
            start = (
                (sequence_length - 1)
                * vocab_size
            )
        else:
            raise ValueError(
                "language model logits must be rank 2 or 3"
            )

        best_id = 0
        best_value = values[start]
        token_id = 1

        while token_id < vocab_size:
            candidate = values[
                start + token_id
            ]

            if candidate > best_value:
                best_value = candidate
                best_id = token_id

            token_id += 1

        return best_id
