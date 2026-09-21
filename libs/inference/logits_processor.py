class LogitsProcessor:
    """
    Handwritten inference-time logit processing.

    Supported controls:
      - temperature
      - repetition penalty
      - top-k
      - top-p / nucleus filtering
      - banned token IDs

    Filtering uses a finite sentinel instead of +/-inf so the rest of SireLLM's
    handwritten numerical stack remains simple and deterministic.
    """

    FILTERED_LOGIT = -1e30

    def __init__(
        self,
        temperature=1.0,
        top_k=None,
        top_p=None,
        repetition_penalty=1.0,
        banned_token_ids=None,
        min_tokens_to_keep=1,
    ):
        if not isinstance(temperature, (int, float)) or temperature <= 0.0:
            raise ValueError("temperature must be > 0")

        if top_k is not None:
            if not isinstance(top_k, int) or top_k <= 0:
                raise ValueError("top_k must be positive int or None")

        if top_p is not None:
            if not isinstance(top_p, (int, float)):
                raise TypeError("top_p must be numeric or None")
            if top_p <= 0.0 or top_p > 1.0:
                raise ValueError("top_p must satisfy 0 < top_p <= 1")

        if (
            not isinstance(repetition_penalty, (int, float))
            or repetition_penalty < 1.0
        ):
            raise ValueError("repetition_penalty must be >= 1")

        if not isinstance(min_tokens_to_keep, int) or min_tokens_to_keep <= 0:
            raise ValueError("min_tokens_to_keep must be positive int")

        if banned_token_ids is None:
            banned_token_ids = []

        self.temperature = float(temperature)
        self.top_k = top_k
        self.top_p = None if top_p is None else float(top_p)
        self.repetition_penalty = float(repetition_penalty)
        self.banned_token_ids = list(banned_token_ids)
        self.min_tokens_to_keep = min_tokens_to_keep

    def process(self, logits, token_history=None):
        if not isinstance(logits, (list, tuple)):
            raise TypeError("logits must be list or tuple")

        if len(logits) == 0:
            raise ValueError("logits must not be empty")

        values = []

        for value in logits:
            if not isinstance(value, (int, float)):
                raise TypeError("logits must contain numbers")
            values.append(float(value))

        history = [] if token_history is None else list(token_history)

        values = self._apply_repetition_penalty(
            values,
            history,
        )

        values = self._apply_temperature(
            values
        )

        values = self._apply_bans(
            values
        )

        if self.top_k is not None:
            values = self._apply_top_k(
                values,
                self.top_k,
            )

        if self.top_p is not None and self.top_p < 1.0:
            values = self._apply_top_p(
                values,
                self.top_p,
            )

        if self._active_count(values) == 0:
            raise ValueError("logit processing removed every token")

        return values

    def _apply_temperature(self, values):
        if self.temperature == 1.0:
            return list(values)

        return [
            value / self.temperature
            for value in values
        ]

    def _apply_repetition_penalty(
        self,
        values,
        history,
    ):
        if self.repetition_penalty == 1.0:
            return list(values)

        output = list(values)
        seen = {}

        for token_id in history:
            if not isinstance(token_id, int):
                raise TypeError("token history must contain ints")
            if token_id < 0 or token_id >= len(output):
                continue
            seen[token_id] = True

        for token_id in seen:
            value = output[token_id]

            # Common repetition-penalty rule: positive logits are divided,
            # negative logits are multiplied, always making repeats less likely.
            if value >= 0.0:
                output[token_id] = (
                    value / self.repetition_penalty
                )
            else:
                output[token_id] = (
                    value * self.repetition_penalty
                )

        return output

    def _apply_bans(self, values):
        output = list(values)

        for token_id in self.banned_token_ids:
            if not isinstance(token_id, int):
                raise TypeError("banned token IDs must be ints")

            if 0 <= token_id < len(output):
                output[token_id] = self.FILTERED_LOGIT

        return output

    def _apply_top_k(self, values, top_k):
        active = []

        index = 0
        while index < len(values):
            if values[index] > self.FILTERED_LOGIT / 2.0:
                active.append((values[index], index))
            index += 1

        if top_k >= len(active):
            return list(values)

        # Deterministic descending sort: larger logit first, then lower token ID.
        active.sort(
            key=lambda pair: (-pair[0], pair[1])
        )

        keep_count = top_k

        if keep_count < self.min_tokens_to_keep:
            keep_count = self.min_tokens_to_keep

        if keep_count > len(active):
            keep_count = len(active)

        keep = {}

        index = 0
        while index < keep_count:
            keep[active[index][1]] = True
            index += 1

        output = []

        index = 0
        while index < len(values):
            if index in keep:
                output.append(values[index])
            else:
                output.append(self.FILTERED_LOGIT)
            index += 1

        return output

    def _apply_top_p(self, values, top_p):
        active = []

        index = 0
        while index < len(values):
            if values[index] > self.FILTERED_LOGIT / 2.0:
                active.append((values[index], index))
            index += 1

        if len(active) <= self.min_tokens_to_keep:
            return list(values)

        active.sort(
            key=lambda pair: (-pair[0], pair[1])
        )

        maximum = active[0][0]
        exponentials = []
        denominator = 0.0

        for logit, token_id in active:
            probability_mass = exp(
                logit - maximum
            )

            exponentials.append(
                (probability_mass, token_id)
            )
            denominator += probability_mass

        cumulative = 0.0
        keep = {}
        kept = 0

        index = 0
        while index < len(exponentials):
            mass, token_id = exponentials[index]
            probability = mass / denominator

            keep[token_id] = True
            cumulative += probability
            kept += 1

            if (
                cumulative >= top_p
                and kept >= self.min_tokens_to_keep
            ):
                break

            index += 1

        output = []

        index = 0
        while index < len(values):
            if index in keep:
                output.append(values[index])
            else:
                output.append(self.FILTERED_LOGIT)
            index += 1

        return output

    def _active_count(self, values):
        count = 0

        for value in values:
            if value > self.FILTERED_LOGIT / 2.0:
                count += 1

        return count
