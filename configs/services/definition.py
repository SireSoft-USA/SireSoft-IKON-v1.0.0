class ServiceDefinition:
    def __init__(
        self,
        service_name,
        instances,
        lease_seconds=60,
        max_consecutive_failures=3,
        endpoint_template=None,
        metadata=None,
    ):
        if not isinstance(service_name, str) or service_name == "":
            raise ValueError("service_name must be non-empty str")

        if not isinstance(instances, (list, tuple)) or len(instances) == 0:
            raise ValueError("instances must be non-empty list/tuple")

        if not isinstance(lease_seconds, int) or lease_seconds <= 0:
            raise ValueError(
                "lease_seconds must be positive int"
            )

        if (
            not isinstance(max_consecutive_failures, int)
            or max_consecutive_failures <= 0
        ):
            raise ValueError(
                "max_consecutive_failures must be positive int"
            )

        if endpoint_template is not None and (
            not isinstance(endpoint_template, str)
            or endpoint_template == ""
        ):
            raise ValueError(
                "endpoint_template must be non-empty str or None"
            )

        if metadata is None:
            metadata = {}

        if not isinstance(metadata, dict):
            raise TypeError("metadata must be dict or None")

        normalized = []
        seen = {}

        for instance in instances:
            if not isinstance(instance, ServiceInstanceConfig):
                raise TypeError(
                    "instances entries must be ServiceInstanceConfig"
                )

            if instance.instance_id in seen:
                raise ValueError(
                    "duplicate instance_id in service: "
                    + instance.instance_id
                )

            seen[instance.instance_id] = True
            normalized.append(instance)

        self.service_name = service_name
        self.instances = normalized
        self.lease_seconds = lease_seconds
        self.max_consecutive_failures = max_consecutive_failures
        self.endpoint_template = endpoint_template
        self.metadata = self._copy(metadata)

    def to_dict(self):
        return {
            "service_name": self.service_name,
            "lease_seconds": self.lease_seconds,
            "max_consecutive_failures": self.max_consecutive_failures,
            "endpoint_template": self.endpoint_template,
            "metadata": self._copy(self.metadata),
            "instances": [
                instance.to_dict()
                for instance in self.instances
            ],
        }

    def _copy(self, value):
        if isinstance(value, dict):
            return {
                key: self._copy(value[key])
                for key in value
            }

        if isinstance(value, (list, tuple)):
            return [
                self._copy(item)
                for item in value
            ]

        return value
