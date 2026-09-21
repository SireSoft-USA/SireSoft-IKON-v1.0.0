class EmbeddingArtifact:
    """
    Protocol-safe persisted state for SireLLM's lexical retrieval embedder.

    The tokenizer signature prevents an IDF state trained with one tokenizer
    from being silently attached to a different tokenization vocabulary.
    """

    FORMAT = "SireLLMEmbeddingState"
    VERSION = 1

    def __init__(
        self,
        tokenizer_signature,
        embedder_state,
    ):
        if (
            not isinstance(
                tokenizer_signature,
                str,
            )
            or tokenizer_signature == ""
        ):
            raise ValueError(
                "tokenizer_signature must be non-empty str"
            )

        if not isinstance(
            embedder_state,
            dict,
        ):
            raise TypeError(
                "embedder_state must be dict"
            )

        self.tokenizer_signature = (
            tokenizer_signature
        )

        self.embedder_state = self._copy(
            embedder_state
        )

        self._validate_state(
            self.embedder_state
        )

    def to_dict(
        self,
    ):
        return {
            "format": self.FORMAT,
            "version": self.VERSION,
            "tokenizer_signature": (
                self.tokenizer_signature
            ),
            "embedder": self._copy(
                self.embedder_state
            ),
        }

    @classmethod
    def from_dict(
        cls,
        value,
    ):
        if not isinstance(
            value,
            dict,
        ):
            raise TypeError(
                "embedding artifact must be dict"
            )

        if value.get(
            "format"
        ) != cls.FORMAT:
            raise ValueError(
                "invalid embedding artifact format"
            )

        if int(
            value.get(
                "version",
                0,
            )
        ) != cls.VERSION:
            raise ValueError(
                "unsupported embedding artifact version"
            )

        return cls(
            tokenizer_signature=value[
                "tokenizer_signature"
            ],
            embedder_state=value[
                "embedder"
            ],
        )

    def _validate_state(
        self,
        state,
    ):
        if state.get(
            "type"
        ) not in (
            None,
            "HashingTFIDFEmbedder",
        ):
            raise ValueError(
                "unsupported embedder state type"
            )

        for key in (
            "dimension",
            "min_n",
            "max_n",
            "use_idf",
            "sublinear_tf",
            "l2_normalize",
            "idf_model",
        ):
            if key not in state:
                raise ValueError(
                    "embedder state missing "
                    + key
                )

        dimension = int(
            state[
                "dimension"
            ]
        )

        min_n = int(
            state[
                "min_n"
            ]
        )

        max_n = int(
            state[
                "max_n"
            ]
        )

        if dimension <= 0:
            raise ValueError(
                "embedder dimension must be positive"
            )

        if min_n <= 0:
            raise ValueError(
                "embedder min_n must be positive"
            )

        if max_n < min_n:
            raise ValueError(
                "embedder max_n must be >= min_n"
            )

        idf = state[
            "idf_model"
        ]

        if not isinstance(
            idf,
            dict,
        ):
            raise TypeError(
                "idf_model state must be dict"
            )

        if int(
            idf.get(
                "dimension",
                0,
            )
        ) != dimension:
            raise ValueError(
                "IDF dimension does not match embedder dimension"
            )

        frequencies = list(
            idf.get(
                "document_frequency",
                [],
            )
        )

        weights = list(
            idf.get(
                "idf",
                [],
            )
        )

        if len(
            frequencies
        ) != dimension:
            raise ValueError(
                "IDF document_frequency dimension mismatch"
            )

        if len(
            weights
        ) != dimension:
            raise ValueError(
                "IDF weight dimension mismatch"
            )

    def _copy(
        self,
        value,
    ):
        if isinstance(
            value,
            dict,
        ):
            result = {}

            for key in value:
                result[
                    key
                ] = self._copy(
                    value[
                        key
                    ]
                )

            return result

        if isinstance(
            value,
            list,
        ):
            return [
                self._copy(
                    item
                )
                for item in value
            ]

        if isinstance(
            value,
            tuple,
        ):
            return [
                self._copy(
                    item
                )
                for item in value
            ]

        return value
