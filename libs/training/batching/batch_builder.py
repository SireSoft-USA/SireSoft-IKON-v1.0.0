class TrainingBatch:
    def __init__(
        self,
        input_ids,
        labels,
        attention_mask,
        loss_mask,
        lengths,
    ):
        self.input_ids = input_ids
        self.labels = labels
        self.attention_mask = attention_mask
        self.loss_mask = loss_mask
        self.lengths = lengths

    def batch_size(self):
        return len(self.input_ids)

    def sequence_length(self):
        if len(self.input_ids) == 0:
            return 0
        return len(self.input_ids[0])

    def active_target_count(self):
        total = 0

        for row in self.loss_mask:
            for value in row:
                if value:
                    total += 1

        return total

    def to_dict(self):
        return {
            "input_ids": [list(row) for row in self.input_ids],
            "labels": [list(row) for row in self.labels],
            "attention_mask": [
                list(row)
                for row in self.attention_mask
            ],
            "loss_mask": [
                list(row)
                for row in self.loss_mask
            ],
            "lengths": list(self.lengths),
        }


class BatchBuilder:
    """
    Builds causal next-token training batches.

    For source tokens:
        [t0, t1, t2, t3]

    it creates:
        input_ids = [t0, t1, t2]
        labels    = [t1, t2, t3]

    Padding labels use ignore_index so CrossEntropyLoss can ignore them.

    When given PackedSequence objects, cross-sample transitions are masked.
    This prevents a model from learning artificial "end of document -> first
    token of next document" transitions introduced only by packing.
    """

    def __init__(
        self,
        pad_token_id,
        ignore_index=-100,
        max_sequence_length=None,
        padding_side="right",
    ):
        if not isinstance(pad_token_id, int):
            raise TypeError("pad_token_id must be int")

        if not isinstance(ignore_index, int):
            raise TypeError("ignore_index must be int")

        if max_sequence_length is not None:
            if (
                not isinstance(max_sequence_length, int)
                or max_sequence_length <= 0
            ):
                raise ValueError(
                    "max_sequence_length must be positive int or None"
                )

        if padding_side not in ("left", "right"):
            raise ValueError(
                "padding_side must be left or right"
            )

        self.pad_token_id = pad_token_id
        self.ignore_index = ignore_index
        self.max_sequence_length = (
            max_sequence_length
        )
        self.padding_side = padding_side

    def build(self, sequences):
        normalized = self._normalize_sources(
            sequences
        )

        raw_inputs = []
        raw_labels = []
        raw_loss_masks = []

        for item in normalized:
            tokens = item["tokens"]
            spans = item["sample_spans"]

            if len(tokens) < 2:
                continue

            usable = list(tokens)

            if self.max_sequence_length is not None:
                maximum_source_tokens = (
                    self.max_sequence_length + 1
                )

                if len(usable) > maximum_source_tokens:
                    usable = usable[
                        :maximum_source_tokens
                    ]

            if len(usable) < 2:
                continue

            input_row = usable[:-1]
            label_row = usable[1:]
            loss_row = [1] * len(label_row)

            self._mask_cross_sample_targets(
                loss_row,
                spans,
                len(usable),
            )

            raw_inputs.append(input_row)
            raw_labels.append(label_row)
            raw_loss_masks.append(loss_row)

        if len(raw_inputs) == 0:
            raise ValueError(
                "no sequence contains enough tokens for next-token training"
            )

        target_length = 0

        for row in raw_inputs:
            if len(row) > target_length:
                target_length = len(row)

        if self.max_sequence_length is not None:
            if target_length > self.max_sequence_length:
                target_length = self.max_sequence_length

        padded_inputs = []
        padded_labels = []
        attention_masks = []
        loss_masks = []
        lengths = []

        row_index = 0

        while row_index < len(raw_inputs):
            input_row = raw_inputs[row_index]
            label_row = raw_labels[row_index]
            loss_row = raw_loss_masks[row_index]

            if len(input_row) > target_length:
                input_row = input_row[:target_length]
                label_row = label_row[:target_length]
                loss_row = loss_row[:target_length]

            real_length = len(input_row)
            pad_count = (
                target_length - real_length
            )

            if self.padding_side == "right":
                padded_input = (
                    input_row
                    + [self.pad_token_id] * pad_count
                )

                padded_label = (
                    label_row
                    + [self.ignore_index] * pad_count
                )

                attention = (
                    [1] * real_length
                    + [0] * pad_count
                )

                padded_loss = (
                    loss_row
                    + [0] * pad_count
                )

            else:
                padded_input = (
                    [self.pad_token_id] * pad_count
                    + input_row
                )

                padded_label = (
                    [self.ignore_index] * pad_count
                    + label_row
                )

                attention = (
                    [0] * pad_count
                    + [1] * real_length
                )

                padded_loss = (
                    [0] * pad_count
                    + loss_row
                )

            # Guarantee ignored labels wherever loss mask is zero.
            position = 0

            while position < target_length:
                if padded_loss[position] == 0:
                    padded_label[position] = (
                        self.ignore_index
                    )

                position += 1

            padded_inputs.append(padded_input)
            padded_labels.append(padded_label)
            attention_masks.append(attention)
            loss_masks.append(padded_loss)
            lengths.append(real_length)

            row_index += 1

        return TrainingBatch(
            padded_inputs,
            padded_labels,
            attention_masks,
            loss_masks,
            lengths,
        )

    def _normalize_sources(self, sequences):
        if not isinstance(sequences, (list, tuple)):
            raise TypeError(
                "sequences must be list or tuple"
            )

        normalized = []

        for sequence in sequences:
            if hasattr(sequence, "tokens"):
                tokens = list(sequence.tokens)

                spans = []

                if hasattr(
                    sequence,
                    "sample_spans",
                ):
                    for span in sequence.sample_spans:
                        spans.append(dict(span))

            else:
                if not isinstance(
                    sequence,
                    (list, tuple),
                ):
                    raise TypeError(
                        "sequence must be token list or PackedSequence"
                    )

                tokens = list(sequence)
                spans = [{
                    "sample_index": len(normalized),
                    "chunk_index": 0,
                    "start": 0,
                    "end": len(tokens),
                }]

            for token in tokens:
                if not isinstance(token, int):
                    raise TypeError(
                        "token IDs must be integers"
                    )

            normalized.append({
                "tokens": tokens,
                "sample_spans": spans,
            })

        return normalized

    def _mask_cross_sample_targets(
        self,
        loss_row,
        spans,
        usable_token_count,
    ):
        if spans is None or len(spans) <= 1:
            return

        index = 1

        while index < len(spans):
            start = spans[index].get("start")

            if (
                isinstance(start, int)
                and start > 0
                and start < usable_token_count
            ):
                label_position = start - 1

                if (
                    label_position >= 0
                    and label_position < len(loss_row)
                ):
                    loss_row[label_position] = 0

            index += 1
