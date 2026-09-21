class GreedySampler:
    """
    Deterministic argmax sampler.
    """

    def sample(self, logits):
        if not isinstance(logits, (list, tuple)) or len(logits) == 0:
            raise ValueError("logits must be a non-empty sequence")

        best_index = 0
        best_value = logits[0]

        index = 1

        while index < len(logits):
            value = logits[index]

            if value > best_value:
                best_value = value
                best_index = index

            index += 1

        return best_index


class CategoricalSampler:
    """
    Samples from a categorical distribution derived from logits.

    Uses SireLLM's deterministic RandomGenerator and handwritten exp().
    """

    def __init__(self, seed=1337):
        self.random = RandomGenerator(seed)

    def sample(self, logits):
        if not isinstance(logits, (list, tuple)) or len(logits) == 0:
            raise ValueError("logits must be a non-empty sequence")

        maximum = None

        for value in logits:
            if not isinstance(value, (int, float)):
                raise TypeError("logits must contain numbers")

            if maximum is None or value > maximum:
                maximum = value

        weights = []
        denominator = 0.0

        for value in logits:
            if value <= -5e29:
                weight = 0.0
            else:
                weight = exp(
                    value - maximum
                )

            weights.append(weight)
            denominator += weight

        if denominator <= 0.0:
            raise ValueError(
                "cannot sample from zero-probability logits"
            )

        draw = self.random.random()
        cumulative = 0.0

        index = 0

        while index < len(weights):
            cumulative += (
                weights[index] / denominator
            )

            if draw < cumulative:
                return index

            index += 1

        # Floating-point tail protection.
        index = len(weights) - 1

        while index >= 0:
            if weights[index] > 0.0:
                return index
            index -= 1

        raise ValueError("no sampleable token")
