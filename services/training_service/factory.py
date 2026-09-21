class TrainingFactory:
    def create(self, job_id, config):
        if not isinstance(config, dict):
            raise TypeError("config must be dict")

        model_config = self._section(config, "model")
        optimizer_config = self._section(
            config, "optimizer", {"type": "adamw"}
        )
        scheduler_config = self._section(
            config, "scheduler", {"type": "constant"}
        )
        training_config = self._section(
            config, "training", {}
        )

        if "vocab_size" not in model_config:
            raise ValueError("model config requires vocab_size")

        vocab_size = model_config["vocab_size"]
        if not isinstance(vocab_size, int) or vocab_size <= 0:
            raise ValueError("vocab_size must be positive int")

        d_model = int(model_config.get("d_model", 32))
        max_seq_len = int(model_config.get("max_seq_len", 128))

        model = LanguageModel(
            vocab_size=vocab_size,
            d_model=d_model,
            num_layers=int(model_config.get("num_layers", 2)),
            num_heads=int(model_config.get("num_heads", 4)),
            d_ff=int(model_config.get("d_ff", d_model * 4)),
            max_seq_len=max_seq_len,
            dropout=float(model_config.get("dropout", 0.0)),
            position_mode=model_config.get("position_mode", "rotary"),
            padding_idx=model_config.get("padding_idx"),
            seed=int(model_config.get("seed", 1337)),
        )

        loss = CrossEntropyLoss(
            reduction="mean",
            ignore_index=int(training_config.get("ignore_index", -100)),
            label_smoothing=float(training_config.get("label_smoothing", 0.0)),
        )

        optimizer = self._optimizer(model, optimizer_config)
        scheduler = self._scheduler(optimizer_config, scheduler_config)

        clipper = None
        clip_norm = training_config.get("gradient_clip_norm", 1.0)
        if clip_norm is not None:
            clipper = GlobalNormClipper(float(clip_norm))

        max_length = training_config.get(
            "max_sequence_length",
            max_seq_len,
        )
        if max_length is not None:
            max_length = int(max_length)

        batch_builder = BatchBuilder(
            pad_token_id=int(training_config.get("pad_token_id", 0)),
            ignore_index=loss.ignore_index,
            max_sequence_length=max_length,
            padding_side=training_config.get("padding_side", "right"),
        )

        trainer = Trainer(
            model=model,
            optimizer=optimizer,
            loss_function=loss,
            scheduler=scheduler,
            gradient_clipper=clipper,
        )

        evaluator = Evaluator(
            model=model,
            loss_function=loss,
        )

        return TrainingJob(
            job_id=job_id,
            config=config,
            model=model,
            optimizer=optimizer,
            scheduler=scheduler,
            loss_function=loss,
            batch_builder=batch_builder,
            trainer=trainer,
            evaluator=evaluator,
            checkpoint_manager=CheckpointManager(),
        )

    def _optimizer(self, model, config):
        kind = str(config.get("type", "adamw")).lower()
        learning_rate = float(config.get("learning_rate", 0.001))

        if kind == "adamw":
            return AdamW(
                model,
                learning_rate=learning_rate,
                beta1=float(config.get("beta1", 0.9)),
                beta2=float(config.get("beta2", 0.999)),
                epsilon=float(config.get("epsilon", 1e-8)),
                weight_decay=float(config.get("weight_decay", 0.01)),
                max_grad_norm=None,
            )

        if kind == "sgd":
            return SGD(
                model,
                learning_rate=learning_rate,
                momentum=float(config.get("momentum", 0.0)),
                dampening=float(config.get("dampening", 0.0)),
                weight_decay=float(config.get("weight_decay", 0.0)),
                nesterov=bool(config.get("nesterov", False)),
            )

        raise ValueError("unsupported optimizer type: " + kind)

    def _scheduler(self, optimizer_config, config):
        kind = str(config.get("type", "constant")).lower()
        base = float(optimizer_config.get("learning_rate", 0.001))

        if kind in ("none", "disabled"):
            return None

        if kind == "constant":
            return ConstantSchedule(
                float(config.get("learning_rate", base))
            )

        if kind == "linear_warmup":
            return LinearWarmupSchedule(
                target_learning_rate=float(
                    config.get("target_learning_rate", base)
                ),
                warmup_steps=int(config.get("warmup_steps", 0)),
                start_learning_rate=float(
                    config.get("start_learning_rate", 0.0)
                ),
            )

        if kind == "cosine":
            return CosineDecaySchedule(
                max_learning_rate=float(
                    config.get("max_learning_rate", base)
                ),
                total_steps=int(config.get("total_steps", 1000)),
                min_learning_rate=float(
                    config.get("min_learning_rate", 0.0)
                ),
            )

        if kind == "warmup_cosine":
            cosine = CosineDecaySchedule(
                max_learning_rate=float(
                    config.get("max_learning_rate", base)
                ),
                total_steps=int(
                    config.get(
                        "decay_steps",
                        config.get("total_steps", 1000),
                    )
                ),
                min_learning_rate=float(
                    config.get("min_learning_rate", 0.0)
                ),
            )

            return WarmupThenSchedule(
                after_schedule=cosine,
                warmup_steps=int(config.get("warmup_steps", 0)),
                start_learning_rate=float(
                    config.get("start_learning_rate", 0.0)
                ),
            )

        raise ValueError("unsupported scheduler type: " + kind)

    def _section(self, config, key, default=None):
        if key not in config:
            return {} if default is None else dict(default)

        value = config[key]
        if not isinstance(value, dict):
            raise TypeError(key + " config must be dict")
        return dict(value)
