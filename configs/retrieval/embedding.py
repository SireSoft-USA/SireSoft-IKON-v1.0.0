class RetrievalEmbeddingConfig:
    def __init__(
        self,
        dimension=256,
        min_n=1,
        max_n=2,
        use_idf=True,
        sublinear_tf=True,
        l2_normalize=True,
    ):
        if not isinstance(
            dimension,
            int,
        ) or dimension <= 0:
            raise ValueError(
                "dimension must be positive int"
            )

        if not isinstance(
            min_n,
            int,
        ) or min_n <= 0:
            raise ValueError(
                "min_n must be positive int"
            )

        if not isinstance(
            max_n,
            int,
        ) or max_n < min_n:
            raise ValueError(
                "max_n must be int >= min_n"
            )

        self.dimension = dimension
        self.min_n = min_n
        self.max_n = max_n
        self.use_idf = bool(
            use_idf
        )
        self.sublinear_tf = bool(
            sublinear_tf
        )
        self.l2_normalize = bool(
            l2_normalize
        )

    def to_dict(
        self,
    ):
        return {
            "dimension": self.dimension,
            "min_n": self.min_n,
            "max_n": self.max_n,
            "use_idf": self.use_idf,
            "sublinear_tf": (
                self.sublinear_tf
            ),
            "l2_normalize": (
                self.l2_normalize
            ),
        }
