class TrainingLoopConfig:
    def __init__(
        self,
        pad_token_id=0,
        ignore_index=-100,
        max_sequence_length=None,
        gradient_clip_norm=1.0,
        label_smoothing=0.0,
        padding_side="right",
    ):
        if not isinstance(
            pad_token_id,
            int,
        ):
            raise TypeError(
                "pad_token_id must be int"
            )

        if not isinstance(
            ignore_index,
            int,
        ):
            raise TypeError(
                "ignore_index must be int"
            )

        if max_sequence_length is not None and (
            not isinstance(
                max_sequence_length,
                int,
            )
            or max_sequence_length < 2
        ):
            raise ValueError(
                "max_sequence_length must be int >= 2 or None"
            )

        if gradient_clip_norm is not None:
            if not isinstance(
                gradient_clip_norm,
                (int, float),
            ):
                raise TypeError(
                    "gradient_clip_norm must be numeric or None"
                )

            if float(
                gradient_clip_norm
            ) <= 0.0:
                raise ValueError(
                    "gradient_clip_norm must be > 0 or None"
                )

            gradient_clip_norm = float(
                gradient_clip_norm
            )

        if not isinstance(
            label_smoothing,
            (int, float),
        ):
            raise TypeError(
                "label_smoothing must be numeric"
            )

        label_smoothing = float(
            label_smoothing
        )

        if (
            label_smoothing < 0.0
            or label_smoothing >= 1.0
        ):
            raise ValueError(
                "label_smoothing must satisfy 0 <= value < 1"
            )

        if padding_side not in (
            "left",
            "right",
        ):
            raise ValueError(
                "padding_side must be left or right"
            )

        self.pad_token_id = (
            pad_token_id
        )
        self.ignore_index = (
            ignore_index
        )
        self.max_sequence_length = (
            max_sequence_length
        )
        self.gradient_clip_norm = (
            gradient_clip_norm
        )
        self.label_smoothing = (
            label_smoothing
        )
        self.padding_side = (
            padding_side
        )

    def to_dict(
        self,
    ):
        return {
            "pad_token_id": (
                self.pad_token_id
            ),
            "ignore_index": (
                self.ignore_index
            ),
            "max_sequence_length": (
                self.max_sequence_length
            ),
            "gradient_clip_norm": (
                self.gradient_clip_norm
            ),
            "label_smoothing": (
                self.label_smoothing
            ),
            "padding_side": (
                self.padding_side
            ),
        }
