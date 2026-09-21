class ServiceDiscoveryConfig:
    def __init__(
        self,
        instances,
        attach_load_balancer=True,
        metadata=None,
    ):
        if not isinstance(
            instances,
            (list, tuple),
        ):
            raise TypeError(
                "instances must be list/tuple"
            )

        normalized = []
        seen = {}

        for instance in instances:
            if not isinstance(
                instance,
                DiscoveryInstanceConfig,
            ):
                raise TypeError(
                    "instance entries must be DiscoveryInstanceConfig"
                )

            if instance.instance_id in seen:
                raise ValueError(
                    "duplicate discovery instance_id: "
                    + instance.instance_id
                )

            seen[instance.instance_id] = True
            normalized.append(instance)

        if metadata is None:
            metadata = {}

        if not isinstance(metadata, dict):
            raise TypeError(
                "metadata must be dict or None"
            )

        self.instances = normalized
        self.attach_load_balancer = bool(
            attach_load_balancer
        )
        self.metadata = self._copy(metadata)

    def enabled_instances(self):
        return [
            instance
            for instance in self.instances
            if instance.enabled
        ]

    def instance_map(self):
        return {
            instance.instance_id: instance
            for instance in self.instances
        }

    def to_dict(self):
        return {
            "instances": [
                instance.to_dict()
                for instance in self.instances
            ],
            "attach_load_balancer": (
                self.attach_load_balancer
            ),
            "metadata": self._copy(
                self.metadata
            ),
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
