class TokenizerService:
    """
    Protocol-facing tokenizer service.

    Supported operations:
      train
      encode
      decode
      info
      vocabulary_entry
      export_state
      load_state
      save_state_file
      load_state_file
    """

    def __init__(
        self,
        manager,
    ):
        if manager is None or not hasattr(
            manager,
            "train",
        ):
            raise TypeError(
                "manager must provide tokenizer operations"
            )

        self.manager = manager

    def handle(
        self,
        request,
    ):
        if not isinstance(
            request,
            ServiceRequest,
        ):
            raise TypeError(
                "request must be ServiceRequest"
            )

        if request.service != "tokenizer_service":
            return self._error(
                request,
                "INVALID_REQUEST",
                "Request targeted the wrong service",
            )

        try:
            operation = (
                request.operation
            )

            if operation == "train":
                return self._train(
                    request
                )

            if operation == "encode":
                return self._encode(
                    request
                )

            if operation == "decode":
                return self._decode(
                    request
                )

            if operation == "info":
                return (
                    ServiceResponse
                    .success_response(
                        request,
                        data={
                            "info": (
                                self.manager
                                .info()
                            ),
                        },
                    )
                )

            if operation == "vocabulary_entry":
                return self._vocabulary_entry(
                    request
                )

            if operation == "export_state":
                return (
                    ServiceResponse
                    .success_response(
                        request,
                        data={
                            "state": (
                                self.manager
                                .export_state()
                            ),
                        },
                    )
                )

            if operation == "load_state":
                return self._load_state(
                    request
                )

            if operation == "save_state_file":
                return self._save_state_file(
                    request
                )

            if operation == "load_state_file":
                return self._load_state_file(
                    request
                )

            return self._error(
                request,
                "INVALID_REQUEST",
                (
                    "Unsupported tokenizer service operation"
                ),
            )

        except FileNotFoundError as error:
            return self._error(
                request,
                "NOT_FOUND",
                str(
                    error
                ),
            )

        except RuntimeError as error:
            return self._error(
                request,
                "MODEL_NOT_READY",
                str(
                    error
                ),
                retryable=True,
            )

        except (
            ValueError,
            TypeError,
            KeyError,
            IndexError,
        ) as error:
            return self._error(
                request,
                "INVALID_REQUEST",
                str(
                    error
                ),
            )

    def _train(
        self,
        request,
    ):
        payload = request.payload

        if "corpus" not in payload:
            raise ValueError(
                "payload requires corpus"
            )

        info = self.manager.train(
            corpus=payload[
                "corpus"
            ],
            vocab_size=payload.get(
                "vocab_size",
                512,
            ),
            min_frequency=payload.get(
                "min_frequency",
                2,
            ),
            special_tokens=payload.get(
                "special_tokens"
            ),
        )

        return (
            ServiceResponse
            .success_response(
                request,
                data={
                    "info": info,
                },
            )
        )

    def _encode(
        self,
        request,
    ):
        payload = request.payload

        if "text" not in payload:
            raise ValueError(
                "payload requires text"
            )

        token_ids = self.manager.encode(
            text=payload[
                "text"
            ],
            add_bos=payload.get(
                "add_bos",
                False,
            ),
            add_eos=payload.get(
                "add_eos",
                False,
            ),
            allow_special=payload.get(
                "allow_special",
                False,
            ),
        )

        return (
            ServiceResponse
            .success_response(
                request,
                data={
                    "token_ids": token_ids,
                    "token_count": len(
                        token_ids
                    ),
                },
            )
        )

    def _decode(
        self,
        request,
    ):
        payload = request.payload

        if "token_ids" not in payload:
            raise ValueError(
                "payload requires token_ids"
            )

        text = self.manager.decode(
            payload[
                "token_ids"
            ],
            skip_special=payload.get(
                "skip_special",
                False,
            ),
        )

        return (
            ServiceResponse
            .success_response(
                request,
                data={
                    "text": text,
                },
            )
        )

    def _vocabulary_entry(
        self,
        request,
    ):
        payload = request.payload

        if "token_id" not in payload:
            raise ValueError(
                "payload requires token_id"
            )

        entry = (
            self.manager
            .vocabulary_entry(
                payload[
                    "token_id"
                ]
            )
        )

        return (
            ServiceResponse
            .success_response(
                request,
                data={
                    "entry": entry,
                },
            )
        )

    def _load_state(
        self,
        request,
    ):
        if "state" not in request.payload:
            raise ValueError(
                "payload requires state"
            )

        info = self.manager.load_state(
            request.payload[
                "state"
            ]
        )

        return (
            ServiceResponse
            .success_response(
                request,
                data={
                    "info": info,
                },
            )
        )

    def _save_state_file(
        self,
        request,
    ):
        if "path" not in request.payload:
            raise ValueError(
                "payload requires path"
            )

        result = (
            self.manager
            .save_state_file(
                request.payload[
                    "path"
                ]
            )
        )

        return (
            ServiceResponse
            .success_response(
                request,
                data={
                    "artifact": result,
                },
            )
        )

    def _load_state_file(
        self,
        request,
    ):
        if "path" not in request.payload:
            raise ValueError(
                "payload requires path"
            )

        info = (
            self.manager
            .load_state_file(
                request.payload[
                    "path"
                ]
            )
        )

        return (
            ServiceResponse
            .success_response(
                request,
                data={
                    "info": info,
                },
            )
        )

    def _error(
        self,
        request,
        code,
        message,
        retryable=False,
    ):
        return (
            ServiceResponse
            .error_response(
                request,
                ProtocolError(
                    code=code,
                    message=message,
                    retryable=retryable,
                ),
            )
        )


def build_tokenizer_manager():
    return TokenizerManager(
        ByteEncoder=ByteEncoder,
        PairCounter=PairCounter,
        Vocabulary=Vocabulary,
        BPETrainer=BPETrainer,
        BPEModel=BPEModel,
        BPETokenizer=BPETokenizer,
        SpecialTokens=SpecialTokens,
    )
