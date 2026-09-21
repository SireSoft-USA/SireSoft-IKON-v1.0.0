class TracingConfigCodec:
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
                "tracing config text must be str"
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
                "tracing config root must be object"
            )

        sampler_value = value.get(
            "sampler",
            {},
        )

        if not isinstance(
            sampler_value,
            dict,
        ):
            raise ValueError(
                "sampler must be object"
            )

        sampler = TraceSamplerConfig(
            numerator=sampler_value.get(
                "numerator",
                1,
            ),
            denominator=sampler_value.get(
                "denominator",
                1,
            ),
        )

        return TracingConfig(
            sampler=sampler,
            persistence_path=value.get(
                "persistence_path"
            ),
            attach_metrics=value.get(
                "attach_metrics",
                True,
            ),
            publish_events=value.get(
                "publish_events",
                False,
            ),
            metadata=value.get(
                "metadata",
                {},
            ),
        )
