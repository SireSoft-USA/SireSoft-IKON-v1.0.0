class MonitoringConfigCodec:
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
                "monitoring config text must be str"
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
                "monitoring config root must be object"
            )

        raw_probes = value.get(
            "probes",
            [],
        )

        if not isinstance(
            raw_probes,
            list,
        ):
            raise ValueError(
                "probes must be list"
            )

        probes = []

        for raw in raw_probes:
            if not isinstance(
                raw,
                dict,
            ):
                raise ValueError(
                    "probe config must be object"
                )

            probes.append(
                MonitoringProbeConfig(
                    probe_id=raw.get(
                        "probe_id"
                    ),
                    service_name=(
                        raw.get(
                            "service_name"
                        )
                    ),
                    operation=raw.get(
                        "operation",
                        "status",
                    ),
                    payload=raw.get(
                        "payload",
                        {},
                    ),
                    required=raw.get(
                        "required",
                        True,
                    ),
                    readiness_path=(
                        raw.get(
                            "readiness_path",
                            [],
                        )
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

        return MonitoringConfig(
            probes=probes,
            attach_load_balancer=(
                value.get(
                    "attach_load_balancer",
                    False,
                )
            ),
            metadata=value.get(
                "metadata",
                {},
            ),
        )
