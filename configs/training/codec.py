class TrainingConfigCodec:
    def __init__(
        self,
        parser=None,
    ):
        self.parser = (
            JSONParser()
            if parser is None
            else parser
        )

    def decode_text(
        self,
        text,
    ):
        if not isinstance(
            text,
            str,
        ):
            raise TypeError(
                "training config text must be str"
            )

        return self.from_dict(
            self.parser.parse(
                text
            )
        )

    def from_dict(
        self,
        value,
    ):
        if not isinstance(
            value,
            dict,
        ):
            raise ValueError(
                "training config root must be object"
            )

        model = value.get(
            "model"
        )

        if not isinstance(
            model,
            dict,
        ):
            raise ValueError(
                "model section must be object"
            )

        optimizer = value.get(
            "optimizer",
            {},
        )

        scheduler = value.get(
            "scheduler",
            {},
        )

        training = value.get(
            "training",
            {},
        )

        for name, section in (
            (
                "optimizer",
                optimizer,
            ),
            (
                "scheduler",
                scheduler,
            ),
            (
                "training",
                training,
            ),
        ):
            if not isinstance(
                section,
                dict,
            ):
                raise ValueError(
                    name
                    + " section must be object"
                )

        model_config = (
            TrainingModelConfig(
                vocab_size=model.get(
                    "vocab_size"
                ),
                d_model=model.get(
                    "d_model",
                    32,
                ),
                num_layers=model.get(
                    "num_layers",
                    2,
                ),
                num_heads=model.get(
                    "num_heads",
                    4,
                ),
                d_ff=model.get(
                    "d_ff"
                ),
                max_seq_len=model.get(
                    "max_seq_len",
                    128,
                ),
                dropout=model.get(
                    "dropout",
                    0.0,
                ),
                position_mode=model.get(
                    "position_mode",
                    "rotary",
                ),
                padding_idx=model.get(
                    "padding_idx"
                ),
                seed=model.get(
                    "seed",
                    1337,
                ),
            )
        )

        optimizer_config = (
            OptimizerConfig(
                optimizer_type=(
                    optimizer.get(
                        "type",
                        "adamw",
                    )
                ),
                learning_rate=(
                    optimizer.get(
                        "learning_rate",
                        0.001,
                    )
                ),
                weight_decay=(
                    optimizer.get(
                        "weight_decay",
                        (
                            0.01
                            if optimizer.get(
                                "type",
                                "adamw",
                            ).lower()
                            == "adamw"
                            else 0.0
                        ),
                    )
                ),
                beta1=optimizer.get(
                    "beta1",
                    0.9,
                ),
                beta2=optimizer.get(
                    "beta2",
                    0.999,
                ),
                epsilon=optimizer.get(
                    "epsilon",
                    1e-8,
                ),
                momentum=optimizer.get(
                    "momentum",
                    0.0,
                ),
                dampening=optimizer.get(
                    "dampening",
                    0.0,
                ),
                nesterov=optimizer.get(
                    "nesterov",
                    False,
                ),
            )
        )

        scheduler_config = (
            SchedulerConfig(
                scheduler_type=(
                    scheduler.get(
                        "type",
                        "constant",
                    )
                ),
                learning_rate=(
                    scheduler.get(
                        "learning_rate"
                    )
                ),
                target_learning_rate=(
                    scheduler.get(
                        "target_learning_rate"
                    )
                ),
                warmup_steps=(
                    scheduler.get(
                        "warmup_steps",
                        0,
                    )
                ),
                start_learning_rate=(
                    scheduler.get(
                        "start_learning_rate",
                        0.0,
                    )
                ),
                max_learning_rate=(
                    scheduler.get(
                        "max_learning_rate"
                    )
                ),
                min_learning_rate=(
                    scheduler.get(
                        "min_learning_rate",
                        0.0,
                    )
                ),
                total_steps=(
                    scheduler.get(
                        "total_steps",
                        1000,
                    )
                ),
                decay_steps=(
                    scheduler.get(
                        "decay_steps"
                    )
                ),
            )
        )

        loop_config = (
            TrainingLoopConfig(
                pad_token_id=(
                    training.get(
                        "pad_token_id",
                        0,
                    )
                ),
                ignore_index=(
                    training.get(
                        "ignore_index",
                        -100,
                    )
                ),
                max_sequence_length=(
                    training.get(
                        "max_sequence_length"
                    )
                ),
                gradient_clip_norm=(
                    training.get(
                        "gradient_clip_norm",
                        1.0,
                    )
                ),
                label_smoothing=(
                    training.get(
                        "label_smoothing",
                        0.0,
                    )
                ),
                padding_side=(
                    training.get(
                        "padding_side",
                        "right",
                    )
                ),
            )
        )

        return TrainingJobConfig(
            model=model_config,
            optimizer=(
                optimizer_config
            ),
            scheduler=(
                scheduler_config
            ),
            training=loop_config,
            metadata=value.get(
                "metadata",
                {},
            ),
        )
