class BPEModel:
    def __init__(self, vocabulary, merges):
        self.vocabulary = vocabulary
        self.merges = list(merges)

    def export_state(self):
        merge_rows = []
        for left, right, new_id in self.merges:
            merge_rows.append({
                "left": left,
                "right": right,
                "new_id": new_id,
            })

        return {
            "vocabulary": self.vocabulary.export_state(),
            "merges": merge_rows,
        }


class BPETrainer:
    """
    Deterministic byte-level BPE trainer.

    Corpus is an iterable of strings. Training repeatedly merges the most
    frequent adjacent token pair using deterministic lexical tie-breaking.
    """

    def __init__(
        self,
        byte_encoder,
        pair_counter,
        vocabulary_factory,
        special_tokens,
    ):
        self.byte_encoder = byte_encoder
        self.pair_counter = pair_counter
        self.vocabulary_factory = vocabulary_factory
        self.special_tokens = special_tokens

    def train(self, corpus, vocab_size=512, min_frequency=2):
        if not isinstance(vocab_size, int) or vocab_size < 256:
            raise ValueError("vocab_size must be int >= 256")
        if not isinstance(min_frequency, int) or min_frequency <= 0:
            raise ValueError("min_frequency must be positive int")

        vocabulary = self.vocabulary_factory()
        sequences = []

        for text in corpus:
            if not isinstance(text, str):
                raise TypeError("corpus items must be strings")
            sequences.append(self.byte_encoder.encode_text(text))

        merges = []

        # Reserve enough IDs for all configured special tokens.
        target_normal_tokens = vocab_size - self.special_tokens.count()
        if target_normal_tokens < 256:
            target_normal_tokens = 256

        while vocabulary.normal_token_count() < target_normal_tokens:
            counts = self.pair_counter.count_sequences(sequences)
            pair, frequency = self.pair_counter.best_pair(
                counts,
                min_frequency=min_frequency,
            )

            if pair is None:
                break

            new_id = vocabulary.add_merge_token(pair[0], pair[1])
            merges.append((pair[0], pair[1], new_id))

            updated = []
            for sequence in sequences:
                updated.append(
                    self._replace_pair(
                        sequence,
                        pair[0],
                        pair[1],
                        new_id,
                    )
                )
            sequences = updated

        vocabulary.finalize_special_tokens(self.special_tokens.all())

        return BPEModel(vocabulary, merges)

    def _replace_pair(self, sequence, left, right, new_id):
        out = []
        i = 0

        while i < len(sequence):
            if (
                i + 1 < len(sequence)
                and sequence[i] == left
                and sequence[i + 1] == right
            ):
                out.append(new_id)
                i += 2
            else:
                out.append(sequence[i])
                i += 1

        return out
