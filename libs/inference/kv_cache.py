class KVCacheLayer:
    """
    Per-layer key/value storage for future cached Transformer decoding.

    Data is stored as:
      keys   -> list of token key vectors
      values -> list of token value vectors

    Current LanguageModel still performs full-context forward passes. This cache
    is the validated storage primitive needed before attention itself is upgraded
    to consume cached K/V tensors.
    """

    def __init__(self, head_dim):
        if not isinstance(head_dim, int) or head_dim <= 0:
            raise ValueError("head_dim must be positive int")

        self.head_dim = head_dim
        self.keys = []
        self.values = []

    def append(self, key_vector, value_vector):
        key = self._validate_vector(
            key_vector,
            "key",
        )

        value = self._validate_vector(
            value_vector,
            "value",
        )

        self.keys.append(key)
        self.values.append(value)
        return self

    def length(self):
        return len(self.keys)

    def clear(self):
        self.keys = []
        self.values = []
        return self

    def trim_left(self, maximum_length):
        if not isinstance(maximum_length, int) or maximum_length < 0:
            raise ValueError(
                "maximum_length must be non-negative int"
            )

        if len(self.keys) <= maximum_length:
            return self

        start = len(self.keys) - maximum_length

        self.keys = self.keys[start:]
        self.values = self.values[start:]
        return self

    def snapshot(self):
        return {
            "head_dim": self.head_dim,
            "keys": [
                list(vector)
                for vector in self.keys
            ],
            "values": [
                list(vector)
                for vector in self.values
            ],
        }

    def _validate_vector(
        self,
        vector,
        name,
    ):
        if not isinstance(vector, (list, tuple)):
            raise TypeError(
                name + " vector must be list or tuple"
            )

        if len(vector) != self.head_dim:
            raise ValueError(
                name + " vector has wrong dimension"
            )

        result = []

        for value in vector:
            if not isinstance(value, (int, float)):
                raise TypeError(
                    name + " vector must contain numbers"
                )
            result.append(float(value))

        return result


class KVCache:
    """
    Multi-layer / multi-head K/V cache container.

    Indexing:
      cache.layer(layer_index, head_index)
    """

    def __init__(
        self,
        num_layers,
        num_heads,
        head_dim,
        max_length=None,
    ):
        if not isinstance(num_layers, int) or num_layers <= 0:
            raise ValueError("num_layers must be positive int")
        if not isinstance(num_heads, int) or num_heads <= 0:
            raise ValueError("num_heads must be positive int")
        if not isinstance(head_dim, int) or head_dim <= 0:
            raise ValueError("head_dim must be positive int")

        if max_length is not None:
            if not isinstance(max_length, int) or max_length <= 0:
                raise ValueError(
                    "max_length must be positive int or None"
                )

        self.num_layers = num_layers
        self.num_heads = num_heads
        self.head_dim = head_dim
        self.max_length = max_length

        self._layers = []

        layer_index = 0

        while layer_index < num_layers:
            heads = []
            head_index = 0

            while head_index < num_heads:
                heads.append(
                    KVCacheLayer(
                        head_dim
                    )
                )
                head_index += 1

            self._layers.append(heads)
            layer_index += 1

    def layer(self, layer_index, head_index):
        if (
            layer_index < 0
            or layer_index >= self.num_layers
        ):
            raise IndexError("layer index out of range")

        if (
            head_index < 0
            or head_index >= self.num_heads
        ):
            raise IndexError("head index out of range")

        return self._layers[
            layer_index
        ][head_index]

    def append(
        self,
        layer_index,
        head_index,
        key_vector,
        value_vector,
    ):
        slot = self.layer(
            layer_index,
            head_index,
        )

        slot.append(
            key_vector,
            value_vector,
        )

        if self.max_length is not None:
            slot.trim_left(
                self.max_length
            )

        return self

    def clear(self):
        for heads in self._layers:
            for slot in heads:
                slot.clear()

        return self

    def common_length(self):
        expected = None

        for heads in self._layers:
            for slot in heads:
                current = slot.length()

                if expected is None:
                    expected = current

                elif current != expected:
                    return None

        if expected is None:
            return 0

        return expected

    def snapshot(self):
        layers = []

        for heads in self._layers:
            layer_rows = []

            for slot in heads:
                layer_rows.append(
                    slot.snapshot()
                )

            layers.append(layer_rows)

        return {
            "num_layers": self.num_layers,
            "num_heads": self.num_heads,
            "head_dim": self.head_dim,
            "max_length": self.max_length,
            "layers": layers,
        }
