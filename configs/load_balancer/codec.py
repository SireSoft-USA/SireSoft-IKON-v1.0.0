class LoadBalancerConfigCodec:
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
                "load balancer config text must be str"
            )

        return self.from_dict(
            self.parser.parse(text)
        )

    def from_dict(self, value):
        if not isinstance(value, dict):
            raise ValueError(
                "load balancer config root must be object"
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
                    "load balancer instance must be object"
                )

            instances.append(
                LoadBalancerInstanceConfig(
                    instance_id=raw.get(
                        "instance_id"
                    ),
                    service_name=raw.get(
                        "service_name"
                    ),
                    handler_key=raw.get(
                        "handler_key"
                    ),
                    max_consecutive_failures=(
                        raw.get(
                            "max_consecutive_failures",
                            3,
                        )
                    ),
                    healthy=raw.get(
                        "healthy",
                        True,
                    ),
                    accepting_requests=(
                        raw.get(
                            "accepting_requests",
                            True,
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

        return LoadBalancerConfig(
            strategy=value.get(
                "strategy",
                "adaptive",
            ),
            max_attempts=value.get(
                "max_attempts",
                2,
            ),
            instances=instances,
            require_service_redundancy=(
                value.get(
                    "require_service_redundancy",
                    False,
                )
            ),
            metadata=value.get(
                "metadata",
                {},
            ),
        )
