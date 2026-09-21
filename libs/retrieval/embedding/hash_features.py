class HashedNGramFeatures:
    """
    Deterministic signed feature hashing over token-ID n-grams.
    """

    def __init__(self, dimension=256, min_n=1, max_n=2, use_sign_hash=True):
        if not isinstance(dimension, int) or dimension <= 0:
            raise ValueError("dimension must be positive int")
        if not isinstance(min_n, int) or min_n <= 0:
            raise ValueError("min_n must be positive int")
        if not isinstance(max_n, int) or max_n < min_n:
            raise ValueError("max_n must be int >= min_n")

        self.dimension = dimension
        self.min_n = min_n
        self.max_n = max_n
        self.use_sign_hash = bool(use_sign_hash)

    def extract(self, token_ids):
        tokens = self._validate_tokens(token_ids)
        counts = {}

        n = self.min_n
        while n <= self.max_n:
            start = 0

            while start + n <= len(tokens):
                feature_hash = self._hash_ngram(
                    tokens,
                    start,
                    n,
                    0xCBF29CE484222325,
                )

                bucket = feature_hash % self.dimension
                sign = 1.0

                if self.use_sign_hash:
                    sign_hash = self._hash_ngram(
                        tokens,
                        start,
                        n,
                        0x84222325CBF29CE4,
                    )

                    if sign_hash & 1:
                        sign = -1.0

                counts[bucket] = (
                    counts.get(bucket, 0.0)
                    + sign
                )

                start += 1

            n += 1

        return counts

    def presence(self, token_ids):
        counts = self.extract(token_ids)
        result = {}

        for bucket in counts:
            result[bucket] = True

        return result

    def _hash_ngram(self, tokens, start, length, seed):
        value = seed & 0xFFFFFFFFFFFFFFFF
        index = start
        end = start + length

        while index < end:
            token = tokens[index] & 0xFFFFFFFFFFFFFFFF
            shift = 0

            while shift < 64:
                byte_value = (token >> shift) & 0xFF
                value ^= byte_value
                value = (
                    value * 0x100000001B3
                ) & 0xFFFFFFFFFFFFFFFF
                shift += 8

            value ^= 0xFF
            value = (
                value * 0x100000001B3
            ) & 0xFFFFFFFFFFFFFFFF

            index += 1

        return value

    def _validate_tokens(self, token_ids):
        if not isinstance(token_ids, (list, tuple)):
            raise TypeError("token_ids must be list or tuple")

        result = []

        for token in token_ids:
            if not isinstance(token, int):
                raise TypeError("token IDs must be integers")
            result.append(token)

        return result
