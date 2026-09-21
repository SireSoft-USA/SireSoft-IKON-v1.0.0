class SafetyLimitsConfig:
    def __init__(
        self,
        input_characters=20000,
        context_characters=100000,
        output_characters=50000,
    ):
        for name, value in (
            ("input_characters", input_characters),
            ("context_characters", context_characters),
            ("output_characters", output_characters),
        ):
            if not isinstance(value, int) or value <= 0:
                raise ValueError(
                    name + " must be positive int"
                )

        self.input_characters = input_characters
        self.context_characters = context_characters
        self.output_characters = output_characters

    def to_dict(self):
        return {
            "input_characters": self.input_characters,
            "context_characters": self.context_characters,
            "output_characters": self.output_characters,
        }
