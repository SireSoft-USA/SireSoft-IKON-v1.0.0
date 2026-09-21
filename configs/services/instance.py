class ServiceInstanceConfig:
    def __init__(self, instance_id, endpoint=None, metadata=None):
        if not isinstance(instance_id, str) or instance_id == "":
            raise ValueError("instance_id must be non-empty str")

        if endpoint is not None and (
            not isinstance(endpoint, str) or endpoint == ""
        ):
            raise ValueError("endpoint must be non-empty str or None")

        if metadata is None:
            metadata = {}

        if not isinstance(metadata, dict):
            raise TypeError("metadata must be dict or None")

        self.instance_id = instance_id
        self.endpoint = endpoint
        self.metadata = self._copy(metadata)

    def to_dict(self):
        return {
            "instance_id": self.instance_id,
            "endpoint": self.endpoint,
            "metadata": self._copy(self.metadata),
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
