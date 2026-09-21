class TokenizerManager:
    """
    Owns the active SireLLM byte-level BPE tokenizer.
    """

    def __init__(
        self,
        ByteEncoder,
        PairCounter,
        Vocabulary,
        BPETrainer,
        BPEModel,
        BPETokenizer,
        SpecialTokens,
        state_codec=None,
    ):
        self.ByteEncoder = ByteEncoder
        self.PairCounter = PairCounter
        self.Vocabulary = Vocabulary
        self.BPETrainer = BPETrainer
        self.BPEModel = BPEModel
        self.BPETokenizer = BPETokenizer
        self.SpecialTokens = SpecialTokens

        self.state_codec = (
            TokenizerStateCodec()
            if state_codec is None
            else state_codec
        )

        self.model = None
        self.tokenizer = None
        self.special_tokens = None
        self.artifact = None

    def ready(self):
        return (
            self.model is not None
            and self.tokenizer is not None
            and self.artifact is not None
        )

    def train(
        self,
        corpus,
        vocab_size=512,
        min_frequency=2,
        special_tokens=None,
    ):
        if not isinstance(
            corpus,
            (list, tuple),
        ):
            corpus = list(
                corpus
            )

        if len(corpus) == 0:
            raise ValueError(
                "training corpus must not be empty"
            )

        for text in corpus:
            if not isinstance(text, str):
                raise TypeError(
                    "training corpus items must be strings"
                )

        specials = self.SpecialTokens(
            special_tokens
        )

        byte_encoder = self.ByteEncoder()

        trainer = self.BPETrainer(
            byte_encoder=byte_encoder,
            pair_counter=self.PairCounter(),
            vocabulary_factory=self.Vocabulary,
            special_tokens=specials,
        )

        model = trainer.train(
            corpus,
            vocab_size=vocab_size,
            min_frequency=min_frequency,
        )

        tokenizer = self.BPETokenizer(
            model,
            byte_encoder,
            specials,
        )

        artifact = (
            TokenizerArtifact
            .from_model(
                model=model,
                special_tokens=specials,
                target_vocab_size=vocab_size,
                min_frequency=min_frequency,
            )
        )

        self.model = model
        self.tokenizer = tokenizer
        self.special_tokens = specials
        self.artifact = artifact

        return self.info()

    def encode(
        self,
        text,
        add_bos=False,
        add_eos=False,
        allow_special=False,
    ):
        self._require_ready()

        return self.tokenizer.encode(
            text,
            add_bos=bool(
                add_bos
            ),
            add_eos=bool(
                add_eos
            ),
            allow_special=bool(
                allow_special
            ),
        )

    def decode(
        self,
        token_ids,
        skip_special=False,
    ):
        self._require_ready()

        return self.tokenizer.decode(
            token_ids,
            skip_special=bool(
                skip_special
            ),
        )

    def export_state(
        self,
    ):
        self._require_ready()

        return self.artifact.to_dict()

    def load_state(
        self,
        state,
    ):
        artifact = (
            TokenizerArtifact
            .from_dict(
                state
            )
        )

        model, specials = (
            artifact.rebuild_model(
                self.Vocabulary,
                self.BPEModel,
                self.SpecialTokens,
            )
        )

        byte_encoder = self.ByteEncoder()

        tokenizer = self.BPETokenizer(
            model,
            byte_encoder,
            specials,
        )

        self.model = model
        self.tokenizer = tokenizer
        self.special_tokens = specials
        self.artifact = artifact

        return self.info()

    def save_state_file(
        self,
        path,
    ):
        self._require_ready()

        return self.state_codec.save(
            path,
            self.artifact,
        )

    def load_state_file(
        self,
        path,
    ):
        artifact = (
            self.state_codec.load(
                path
            )
        )

        return self.load_state(
            artifact.to_dict()
        )

    def info(
        self,
    ):
        if not self.ready():
            return {
                "ready": False,
                "vocabulary_size": 0,
                "normal_token_count": 0,
                "special_token_count": 0,
                "merge_count": 0,
                "special_tokens": [],
                "target_vocab_size": None,
                "min_frequency": None,
            }

        vocabulary = (
            self.model.vocabulary
        )

        return {
            "ready": True,
            "vocabulary_size": (
                vocabulary.size()
            ),
            "normal_token_count": (
                vocabulary
                .normal_token_count()
            ),
            "special_token_count": (
                vocabulary
                .special_token_count()
            ),
            "merge_count": len(
                self.model.merges
            ),
            "special_tokens": (
                self.special_tokens.all()
            ),
            "target_vocab_size": (
                self.artifact
                .target_vocab_size
            ),
            "min_frequency": (
                self.artifact
                .min_frequency
            ),
        }

    def vocabulary_entry(
        self,
        token_id,
    ):
        self._require_ready()

        if not isinstance(
            token_id,
            int,
        ):
            raise TypeError(
                "token_id must be int"
            )

        vocabulary = (
            self.model.vocabulary
        )

        if (
            token_id < 0
            or token_id
            >= vocabulary.size()
        ):
            raise IndexError(
                "token_id out of vocabulary range"
            )

        if vocabulary.is_special(
            token_id
        ):
            return {
                "token_id": token_id,
                "kind": "special",
                "token": (
                    vocabulary
                    .special_token(
                        token_id
                    )
                ),
                "bytes": None,
            }

        values = list(
            vocabulary.token_bytes(
                token_id
            )
        )

        text = None

        try:
            text = (
                self.ByteEncoder()
                .decode_bytes(
                    values
                )
            )
        except ValueError:
            text = None

        return {
            "token_id": token_id,
            "kind": (
                "byte"
                if token_id < 256
                else "merge"
            ),
            "token": text,
            "bytes": values,
        }

    def _require_ready(
        self,
    ):
        if not self.ready():
            raise RuntimeError(
                "tokenizer is not trained or loaded"
            )
