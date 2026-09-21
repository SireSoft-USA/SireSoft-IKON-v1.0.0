class PairCounter:
    """
    Counts adjacent token pairs for BPE training.
    """

    def count_sequences(self, sequences):
        counts = {}

        for sequence in sequences:
            if not isinstance(sequence, list):
                raise TypeError("each sequence must be list")

            i = 0
            while i + 1 < len(sequence):
                pair = (sequence[i], sequence[i + 1])
                counts[pair] = counts.get(pair, 0) + 1
                i += 1

        return counts

    def best_pair(self, counts, min_frequency=2):
        if not isinstance(counts, dict):
            raise TypeError("counts must be dict")
        if not isinstance(min_frequency, int) or min_frequency <= 0:
            raise ValueError("min_frequency must be positive int")

        best = None
        best_count = -1

        for pair in counts:
            count = counts[pair]

            if count < min_frequency:
                continue

            if count > best_count:
                best = pair
                best_count = count

            elif count == best_count and best is not None:
                if pair < best:
                    best = pair

        if best is None:
            return None, 0

        return best, best_count
