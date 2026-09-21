class InferenceConfigCodec:
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
                "inference config text must be str"
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
                "inference config root must be object"
            )

        generation = value.get(
            "generation",
            {},
        )

        if not isinstance(
            generation,
            dict,
        ):
            raise ValueError(
                "generation section must be object"
            )

        return InferenceConfig(
            model_id=value.get(
                "model_id"
            ),
            load_mode=value.get(
                "load_mode",
                "active",
            ),
            version=value.get(
                "version"
            ),
            generation=(
                GenerationConfig(
                    max_new_tokens=(
                        generation.get(
                            "max_new_tokens",
                            32,
                        )
                    ),
                    eos_token_ids=(
                        generation.get(
                            "eos_token_ids",
                            [],
                        )
                    ),
                    sampler=(
                        generation.get(
                            "sampler",
                            "greedy",
                        )
                    ),
                    seed=(
                        generation.get(
                            "seed",
                            1337,
                        )
                    ),
                    temperature=(
                        generation.get(
                            "temperature",
                            1.0,
                        )
                    ),
                    top_k=(
                        generation.get(
                            "top_k"
                        )
                    ),
                    top_p=(
                        generation.get(
                            "top_p"
                        )
                    ),
                    repetition_penalty=(
                        generation.get(
                            "repetition_penalty",
                            1.0,
                        )
                    ),
                    banned_token_ids=(
                        generation.get(
                            "banned_token_ids",
                            [],
                        )
                    ),
                    allow_prompt_truncation=(
                        generation.get(
                            "allow_prompt_truncation",
                            True,
                        )
                    ),
                )
            ),
            metadata=value.get(
                "metadata",
                {},
            ),
        )
