class CheckpointInspector:
    """
    Verifies SireLLM checkpoint files without constructing a model.

    It validates the binary checkpoint envelope/checksum through CheckpointCodec,
    reports file checksum/size, counts serialized model parameters, and extracts
    architecture metadata when training_service stored job_config.
    """

    FNV_OFFSET = 0xCBF29CE484222325
    FNV_PRIME = 0x100000001B3
    MASK = 0xFFFFFFFFFFFFFFFF

    def __init__(
        self,
        codec=None,
    ):
        self.codec = (
            CheckpointCodec()
            if codec is None
            else codec
        )

    def inspect(self, path):
        if not isinstance(path, str) or path == "":
            raise ValueError(
                "checkpoint path must be non-empty str"
            )

        handle = open(
            path,
            "rb",
        )

        try:
            data = handle.read()
        finally:
            handle.close()

        if len(data) == 0:
            raise ValueError(
                "checkpoint file is empty"
            )

        payload = self.codec.decode(
            data
        )

        if not isinstance(payload, dict):
            raise ValueError(
                "checkpoint payload must be dict"
            )

        if payload.get("format") != "SireLLMCheckpoint":
            raise ValueError(
                "not a SireLLM checkpoint payload"
            )

        if int(payload.get("version", 0)) != 1:
            raise ValueError(
                "unsupported SireLLM checkpoint payload version"
            )

        model_state = payload.get(
            "model"
        )

        if not isinstance(model_state, dict):
            raise ValueError(
                "checkpoint model state must be dict"
            )

        metadata = payload.get(
            "metadata",
            {},
        )

        if not isinstance(metadata, dict):
            raise ValueError(
                "checkpoint metadata must be dict"
            )

        architecture = self._architecture(
            metadata
        )

        checksum = self._fnv1a64(
            data
        )

        return {
            "path": path,
            "valid": True,
            "format": payload["format"],
            "version": int(
                payload["version"]
            ),
            "bytes": len(data),
            "checksum": self._hex64(
                checksum
            ),
            "parameter_count": (
                self._parameter_count(
                    model_state
                )
            ),
            "parameter_tensors": len(
                model_state
            ),
            "architecture": architecture,
            "metadata": self._copy(
                metadata
            ),
            "has_optimizer": (
                payload.get(
                    "optimizer"
                )
                is not None
            ),
            "has_scheduler": (
                payload.get(
                    "scheduler"
                )
                is not None
            ),
            "has_trainer": (
                payload.get(
                    "trainer"
                )
                is not None
            ),
        }

    def try_inspect(self, path):
        try:
            return self.inspect(
                path
            )

        except Exception as error:
            return {
                "path": path,
                "valid": False,
                "error_type": type(
                    error
                ).__name__,
                "error": str(
                    error
                ),
            }

    def discover(self, paths):
        if not isinstance(
            paths,
            (list, tuple),
        ):
            paths = list(
                paths
            )

        results = []

        for path in paths:
            results.append(
                self.try_inspect(
                    path
                )
            )

        return results

    def _parameter_count(
        self,
        model_state,
    ):
        total = 0

        for name in model_state:
            row = model_state[
                name
            ]

            if not isinstance(row, dict):
                raise ValueError(
                    "model state entry must be dict: "
                    + str(name)
                )

            data = row.get(
                "data"
            )

            shape = row.get(
                "shape"
            )

            if not isinstance(data, list):
                raise ValueError(
                    "model state entry data must be list: "
                    + str(name)
                )

            if not isinstance(shape, list):
                raise ValueError(
                    "model state entry shape must be list: "
                    + str(name)
                )

            expected = 1

            for dimension in shape:
                dimension = int(
                    dimension
                )

                if dimension < 0:
                    raise ValueError(
                        "model state contains negative dimension"
                    )

                expected *= dimension

            if expected != len(data):
                raise ValueError(
                    "model state shape/data mismatch: "
                    + str(name)
                )

            total += len(
                data
            )

        return total

    def _architecture(
        self,
        metadata,
    ):
        job_config = metadata.get(
            "job_config"
        )

        if not isinstance(
            job_config,
            dict,
        ):
            return {}

        model_config = job_config.get(
            "model"
        )

        if not isinstance(
            model_config,
            dict,
        ):
            return {}

        return self._copy(
            model_config
        )

    def _fnv1a64(
        self,
        data,
    ):
        value = self.FNV_OFFSET

        for byte_value in data:
            value ^= byte_value
            value = (
                value
                * self.FNV_PRIME
            ) & self.MASK

        return value

    def _hex64(
        self,
        value,
    ):
        digits = (
            "0123456789abcdef"
        )

        result = ""
        index = 0

        while index < 16:
            shift = (
                60
                - index * 4
            )

            result += digits[
                (
                    value
                    >> shift
                )
                & 0xF
            ]

            index += 1

        return result

    def _copy(self, value):
        if isinstance(value, dict):
            result = {}

            for key in value:
                result[key] = self._copy(
                    value[key]
                )

            return result

        if isinstance(value, list):
            return [
                self._copy(item)
                for item in value
            ]

        if isinstance(value, tuple):
            return [
                self._copy(item)
                for item in value
            ]

        return value
