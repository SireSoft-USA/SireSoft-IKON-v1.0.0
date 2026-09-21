class ServiceConfigCodec:
    def __init__(self, parser=None):
        self.parser = (
            JSONParser()
            if parser is None
            else parser
        )

    def decode_text(self, text):
        if not isinstance(text, str):
            raise TypeError("service config text must be str")

        return self.from_dict(
            self.parser.parse(text)
        )

    def from_dict(self, value):
        if not isinstance(value, dict):
            raise ValueError(
                "service config root must be object"
            )

        services = value.get("services")

        if not isinstance(services, list):
            raise ValueError("services must be list")

        catalog = ServiceConfigCatalog()
        global_instance_ids = {}

        for item in services:
            if not isinstance(item, dict):
                raise ValueError("service entry must be object")

            raw_instances = item.get("instances")

            if not isinstance(raw_instances, list):
                raise ValueError("instances must be list")

            instances = []

            for raw_instance in raw_instances:
                if not isinstance(raw_instance, dict):
                    raise ValueError(
                        "instance entry must be object"
                    )

                instance_id = raw_instance.get("instance_id")

                if instance_id in global_instance_ids:
                    raise ValueError(
                        "duplicate global instance_id: "
                        + str(instance_id)
                    )

                instance = ServiceInstanceConfig(
                    instance_id=instance_id,
                    endpoint=raw_instance.get("endpoint"),
                    metadata=raw_instance.get(
                        "metadata",
                        {},
                    ),
                )

                global_instance_ids[
                    instance.instance_id
                ] = True

                instances.append(instance)

            catalog.add(
                ServiceDefinition(
                    service_name=item.get(
                        "service_name"
                    ),
                    instances=instances,
                    lease_seconds=item.get(
                        "lease_seconds",
                        60,
                    ),
                    max_consecutive_failures=item.get(
                        "max_consecutive_failures",
                        3,
                    ),
                    endpoint_template=item.get(
                        "endpoint_template"
                    ),
                    metadata=item.get(
                        "metadata",
                        {},
                    ),
                )
            )

        return catalog
