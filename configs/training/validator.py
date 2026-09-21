class TrainingConfigValidator:
    def validate(
        self,
        config,
    ):
        if not isinstance(
            config,
            TrainingJobConfig,
        ):
            raise TypeError(
                "config must be TrainingJobConfig"
            )

        errors = []
        warnings = []

        model = config.model
        loop = config.training
        scheduler = (
            config.scheduler
        )

        if (
            loop.pad_token_id < 0
            or loop.pad_token_id
            >= model.vocab_size
        ):
            errors.append({
                "code": (
                    "PAD_TOKEN_OUT_OF_RANGE"
                ),
                "message": (
                    "pad_token_id must be inside model vocabulary"
                ),
            })

        if (
            loop.max_sequence_length
            is not None
            and loop.max_sequence_length
            > model.max_seq_len
        ):
            errors.append({
                "code": (
                    "TRAIN_SEQUENCE_EXCEEDS_MODEL_LIMIT"
                ),
                "message": (
                    "training max_sequence_length exceeds model max_seq_len"
                ),
            })

        if (
            model.padding_idx
            is not None
            and model.padding_idx
            != loop.pad_token_id
        ):
            warnings.append({
                "code": (
                    "PADDING_ID_MISMATCH"
                ),
                "message": (
                    "model padding_idx differs from training pad_token_id"
                ),
            })

        if (
            scheduler.scheduler_type
            == "linear_warmup"
            and scheduler.warmup_steps
            == 0
        ):
            warnings.append({
                "code": (
                    "ZERO_WARMUP_STEPS"
                ),
                "message": (
                    "linear_warmup scheduler has zero warmup steps"
                ),
            })

        if (
            scheduler.scheduler_type
            == "warmup_cosine"
            and scheduler.warmup_steps
            >= (
                scheduler.decay_steps
                if scheduler.decay_steps
                is not None
                else scheduler.total_steps
            )
        ):
            warnings.append({
                "code": (
                    "WARMUP_DOMINATES_DECAY"
                ),
                "message": (
                    "warmup steps are greater than or equal to configured decay steps"
                ),
            })

        if (
            config.optimizer.optimizer_type
            == "sgd"
            and config.optimizer.momentum
            == 0.0
        ):
            warnings.append({
                "code": (
                    "SGD_WITHOUT_MOMENTUM"
                ),
                "message": (
                    "SGD is configured without momentum"
                ),
            })

        return {
            "valid": (
                len(
                    errors
                )
                == 0
            ),
            "error_count": len(
                errors
            ),
            "warning_count": len(
                warnings
            ),
            "errors": errors,
            "warnings": warnings,
        }

    def require_valid(
        self,
        config,
    ):
        result = self.validate(
            config
        )

        if not result[
            "valid"
        ]:
            first = result[
                "errors"
            ][
                0
            ]

            raise ValueError(
                first[
                    "code"
                ]
                + ": "
                + first[
                    "message"
                ]
            )

        return result
