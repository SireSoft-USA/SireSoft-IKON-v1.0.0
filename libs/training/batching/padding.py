class PaddingResult:
    def __init__(self, sequences, attention_mask, lengths, target_length):
        self.sequences = sequences
        self.attention_mask = attention_mask
        self.lengths = lengths
        self.target_length = target_length

    def to_dict(self):
        return {
            "sequences": [list(row) for row in self.sequences],
            "attention_mask": [list(row) for row in self.attention_mask],
            "lengths": list(self.lengths),
            "target_length": self.target_length,
        }


class Padder:
    """
    Pads integer token sequences without external libraries.

    attention_mask convention:
      1 -> real token
      0 -> padding token
    """

    def __init__(self, pad_token_id, side="right"):
        if not isinstance(pad_token_id, int):
            raise TypeError("pad_token_id must be int")
        if side not in ("left", "right"):
            raise ValueError("side must be left or right")

        self.pad_token_id = pad_token_id
        self.side = side

    def pad(self, sequences, target_length=None, truncate=False):
        normalized = self._validate_sequences(sequences)

        lengths = []
        maximum = 0

        for sequence in normalized:
            length = len(sequence)
            lengths.append(length)

            if length > maximum:
                maximum = length

        if target_length is None:
            target_length = maximum

        if not isinstance(target_length, int) or target_length < 0:
            raise ValueError("target_length must be non-negative int")

        padded = []
        masks = []
        final_lengths = []

        index = 0

        while index < len(normalized):
            sequence = list(normalized[index])

            if len(sequence) > target_length:
                if not truncate:
                    raise ValueError(
                        "sequence length exceeds target_length"
                    )

                if self.side == "right":
                    sequence = sequence[:target_length]
                else:
                    sequence = sequence[
                        len(sequence) - target_length:
                    ]

            real_length = len(sequence)
            pad_count = target_length - real_length

            if self.side == "right":
                row = (
                    sequence
                    + [self.pad_token_id] * pad_count
                )

                mask = (
                    [1] * real_length
                    + [0] * pad_count
                )

            else:
                row = (
                    [self.pad_token_id] * pad_count
                    + sequence
                )

                mask = (
                    [0] * pad_count
                    + [1] * real_length
                )

            padded.append(row)
            masks.append(mask)
            final_lengths.append(real_length)

            index += 1

        return PaddingResult(
            padded,
            masks,
            final_lengths,
            target_length,
        )

    def _validate_sequences(self, sequences):
        if not isinstance(sequences, (list, tuple)):
            raise TypeError("sequences must be list or tuple")

        result = []

        for sequence in sequences:
            if not isinstance(sequence, (list, tuple)):
                raise TypeError(
                    "each token sequence must be list or tuple"
                )

            row = []

            for token in sequence:
                if not isinstance(token, int):
                    raise TypeError("token IDs must be integers")
                row.append(token)

            result.append(row)

        return result
