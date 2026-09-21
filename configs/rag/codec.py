class RAGConfigCodec:
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
        if not isinstance(text, str):
            raise TypeError(
                "RAG config text must be str"
            )

        return self.from_dict(
            self.parser.parse(text)
        )

    def from_dict(
        self,
        value,
    ):
        if not isinstance(value, dict):
            raise ValueError(
                "RAG config root must be object"
            )

        retrieval = value.get(
            "retrieval",
            {},
        )
        generation = value.get(
            "generation",
            {},
        )
        prompt = value.get(
            "prompt",
            {},
        )

        for name, section in (
            ("retrieval", retrieval),
            ("generation", generation),
            ("prompt", prompt),
        ):
            if not isinstance(
                section,
                dict,
            ):
                raise ValueError(
                    name
                    + " section must be object"
                )

        return RAGConfig(
            retrieval=(
                RAGRetrievalConfig(
                    candidate_k=(
                        retrieval.get(
                            "candidate_k",
                            20,
                        )
                    ),
                    top_k=(
                        retrieval.get(
                            "top_k",
                            5,
                        )
                    ),
                    min_score=(
                        retrieval.get(
                            "min_score"
                        )
                    ),
                    use_mmr=(
                        retrieval.get(
                            "use_mmr",
                            True,
                        )
                    ),
                    mmr_lambda=(
                        retrieval.get(
                            "mmr_lambda",
                            0.75,
                        )
                    ),
                    similarity_weight=(
                        retrieval.get(
                            "similarity_weight",
                            1.0,
                        )
                    ),
                    dataset_boosts=(
                        retrieval.get(
                            "dataset_boosts"
                        )
                    ),
                    document_boosts=(
                        retrieval.get(
                            "document_boosts"
                        )
                    ),
                    metadata_boosts=(
                        retrieval.get(
                            "metadata_boosts"
                        )
                    ),
                )
            ),
            generation=(
                RAGGenerationConfig(
                    max_new_tokens=(
                        generation.get(
                            "max_new_tokens",
                            64,
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
                    top_k_sampling=(
                        generation.get(
                            "top_k_sampling"
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
                )
            ),
            prompt=(
                RAGPromptConfig(
                    system_message=(
                        prompt.get(
                            "system_message"
                        )
                    ),
                    compact=(
                        prompt.get(
                            "compact",
                            True,
                        )
                    ),
                )
            ),
            max_context_tokens=value.get(
                "max_context_tokens",
                512,
            ),
            max_prompt_tokens=value.get(
                "max_prompt_tokens"
            ),
            metadata=value.get(
                "metadata",
                {},
            ),
        )
