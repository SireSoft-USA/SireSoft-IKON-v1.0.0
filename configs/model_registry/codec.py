class ModelRegistryConfigCodec:
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
                "model-registry config text must be str"
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
                "model-registry config root must be object"
            )

        raw_versions = value.get(
            "versions"
        )

        if not isinstance(
            raw_versions,
            list,
        ) or len(
            raw_versions
        ) == 0:
            raise ValueError(
                "versions must be non-empty list"
            )

        versions = []

        for raw in raw_versions:
            if not isinstance(
                raw,
                dict,
            ):
                raise ValueError(
                    "model version config entry must be object"
                )

            versions.append(
                ModelVersionConfig(
                    model_id=raw.get(
                        "model_id"
                    ),
                    version=raw.get(
                        "version"
                    ),
                    checkpoint_path=raw.get(
                        "checkpoint_path"
                    ),
                    stage=raw.get(
                        "stage",
                        False,
                    ),
                    promote=raw.get(
                        "promote",
                        False,
                    ),
                    verify=raw.get(
                        "verify",
                        False,
                    ),
                    enabled=raw.get(
                        "enabled",
                        True,
                    ),
                    metadata=raw.get(
                        "metadata",
                        {},
                    ),
                )
            )

        return ModelRegistryConfig(
            versions=versions,
            verify_all=value.get(
                "verify_all",
                False,
            ),
            fail_on_verification_error=value.get(
                "fail_on_verification_error",
                True,
            ),
            metadata=value.get(
                "metadata",
                {},
            ),
        )
