class ServiceDiscoveryConfigCodec:
    def __init__(
        self,
        parser=None,
    ):
        self.parser = (
            JSONParser()
            if parser is None
            else parser
        )

    def decode_text(self, text):
        if not isinstance(text, str):
            raise TypeError(
                "service discovery config text must be str"
            )

        return self.from_dict(
            self.parser.parse(text)
        )

    def from_dict(self, value):
        if not isinstance(value, dict):
            raise ValueError(
                "service discovery config root must be object"
            )

        raw_instances = value.get(
            "instances",
            [],
        )

        if not isinstance(
            raw_instances,
            list,
        ):
            raise ValueError(
                "instances must be list"
            )

        instances = []

        for raw in raw_instances:
            if not isinstance(raw, dict):
                raise ValueError(
                    "service discovery instance must be object"
                )

            instances.append(
                DiscoveryInstanceConfig(
                    instance_id=raw.get(
                        "instance_id"
                    ),
                    service_name=raw.get(
                        "service_name"
                    ),
                    endpoint=raw.get(
                        "endpoint"
                    ),
                    lease_seconds=raw.get(
                        "lease_seconds",
                        60,
                    ),
                    local_handler_key=raw.get(
                        "local_handler_key"
                    ),
                    max_consecutive_failures=raw.get(
                        "max_consecutive_failures",
                        3,
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

        return ServiceDiscoveryConfig(
            instances=instances,
            attach_load_balancer=value.get(
                "attach_load_balancer",
                True,
            ),
            metadata=value.get(
                "metadata",
                {},
            ),
        )
