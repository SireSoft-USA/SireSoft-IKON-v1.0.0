class PackedSequence:
    """
    One packed token block plus source-sample boundaries.

    sample_spans contains dictionaries with:
      sample_index
      start        inclusive token index inside packed block
      end          exclusive token index inside packed block

    Separator tokens are intentionally outside sample spans.
    """

    def __init__(self, tokens=None, sample_spans=None):
        self.tokens = [] if tokens is None else list(tokens)
        self.sample_spans = (
            []
            if sample_spans is None
            else [dict(span) for span in sample_spans]
        )

    def token_count(self):
        return len(self.tokens)

    def sample_count(self):
        return len(self.sample_spans)

    def to_dict(self):
        return {
            "tokens": list(self.tokens),
            "sample_spans": [
                dict(span)
                for span in self.sample_spans
            ],
        }


class SequencePacker:
    """
    Greedily packs tokenized samples into fixed-capacity blocks.

    Long samples can be split into multiple chunks. Provenance is retained via
    sample_spans so BatchBuilder can mask cross-sample next-token targets.

    Example with separator 99:
      sample A [1,2], sample B [3,4]
      packed -> [1,2,99,3,4]
      spans  -> A:[0,2], B:[3,5]

    The label from token 99 to token 3 is later ignored, preventing artificial
    cross-document training.
    """

    def __init__(
        self,
        max_tokens,
        separator_token_id=None,
        split_long_sequences=True,
        drop_last=False,
    ):
        if not isinstance(max_tokens, int) or max_tokens <= 1:
            raise ValueError("max_tokens must be int > 1")

        if (
            separator_token_id is not None
            and not isinstance(separator_token_id, int)
        ):
            raise TypeError(
                "separator_token_id must be int or None"
            )

        self.max_tokens = max_tokens
        self.separator_token_id = separator_token_id
        self.split_long_sequences = bool(
            split_long_sequences
        )
        self.drop_last = bool(drop_last)

    def pack(self, sequences):
        validated = self._validate_sequences(sequences)

        result = []
        current = PackedSequence()

        sample_index = 0

        while sample_index < len(validated):
            sequence = validated[sample_index]

            if len(sequence) == 0:
                sample_index += 1
                continue

            chunks = self._chunks_for_sequence(sequence)

            chunk_index = 0

            while chunk_index < len(chunks):
                chunk = chunks[chunk_index]

                separator_cost = 0

                if (
                    current.token_count() > 0
                    and self.separator_token_id is not None
                ):
                    separator_cost = 1

                required = (
                    separator_cost
                    + len(chunk)
                )

                if (
                    current.token_count() > 0
                    and current.token_count() + required
                    > self.max_tokens
                ):
                    result.append(current)
                    current = PackedSequence()
                    separator_cost = 0

                if (
                    current.token_count() > 0
                    and self.separator_token_id is not None
                ):
                    current.tokens.append(
                        self.separator_token_id
                    )

                start = current.token_count()

                for token in chunk:
                    current.tokens.append(token)

                end = current.token_count()

                current.sample_spans.append({
                    "sample_index": sample_index,
                    "chunk_index": chunk_index,
                    "start": start,
                    "end": end,
                })

                if current.token_count() == self.max_tokens:
                    result.append(current)
                    current = PackedSequence()

                chunk_index += 1

            sample_index += 1

        if current.token_count() > 0:
            if not self.drop_last:
                result.append(current)

        return result

    def _chunks_for_sequence(self, sequence):
        if len(sequence) <= self.max_tokens:
            return [list(sequence)]

        if not self.split_long_sequences:
            raise ValueError(
                "sequence exceeds max_tokens and splitting is disabled"
            )

        chunks = []
        start = 0

        while start < len(sequence):
            end = start + self.max_tokens

            if end > len(sequence):
                end = len(sequence)

            chunks.append(
                list(sequence[start:end])
            )

            start = end

        return chunks

    def _validate_sequences(self, sequences):
        if not isinstance(sequences, (list, tuple)):
            raise TypeError("sequences must be list or tuple")

        result = []

        for sequence in sequences:
            if not isinstance(sequence, (list, tuple)):
                raise TypeError(
                    "each sequence must be list or tuple"
                )

            row = []

            for token in sequence:
                if not isinstance(token, int):
                    raise TypeError(
                        "token IDs must be integers"
                    )

                row.append(token)

            result.append(row)

        return result
