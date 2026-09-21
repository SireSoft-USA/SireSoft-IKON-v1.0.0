class TraceSamplerConfig:
    """
    Serializable deterministic trace-sampling configuration.
    """

    def __init__(
        self,
        numerator=1,
        denominator=1,
    ):
        if (
            not isinstance(
                numerator,
                int,
            )
            or numerator < 0
        ):
            raise ValueError(
                "numerator must be non-negative int"
            )

        if (
            not isinstance(
                denominator,
                int,
            )
            or denominator <= 0
        ):
            raise ValueError(
                "denominator must be positive int"
            )

        if numerator > denominator:
            raise ValueError(
                "numerator cannot exceed denominator"
            )

        self.numerator = numerator
        self.denominator = denominator

    def to_dict(
        self,
    ):
        return {
            "numerator": (
                self.numerator
            ),
            "denominator": (
                self.denominator
            ),
        }
