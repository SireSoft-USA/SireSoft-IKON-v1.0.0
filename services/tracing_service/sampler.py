class DeterministicTraceSampler:
    """
    Stable hash-based sampler using the existing handwritten FNV-1a checksum.

    numerator=denominator samples everything. numerator=0 samples nothing.
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

    def should_sample(
        self,
        trace_id,
    ):
        if not isinstance(
            trace_id,
            str,
        ) or trace_id == "":
            raise ValueError(
                "trace_id must be non-empty str"
            )

        if self.numerator == 0:
            return False

        if self.numerator == self.denominator:
            return True

        value = fnv1a64(
            trace_id.encode(
                "utf-8"
            )
        )

        return (
            value
            % self.denominator
        ) < self.numerator

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
