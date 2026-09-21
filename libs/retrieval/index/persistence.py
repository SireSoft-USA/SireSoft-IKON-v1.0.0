class IndexPersistence:
    """
    Binary persistence for FlatVectorIndex using SireLLM core serialization.

    The payload has a magic/version/checksum envelope and a deterministic
    recursively encoded state. No pickle, json, struct, NumPy or third-party
    serialization is used.
    """

    MAGIC = b"SLLMVIDX"
    VERSION = 1

    TAG_NONE = 0
    TAG_FALSE = 1
    TAG_TRUE = 2
    TAG_INT = 3
    TAG_FLOAT = 4
    TAG_TEXT = 5
    TAG_LIST = 6
    TAG_DICT = 7

    def save(self, path, index):
        if not isinstance(path, str) or path == "":
            raise ValueError(
                "path must be non-empty str"
            )

        if not isinstance(
            index,
            FlatVectorIndex,
        ):
            raise TypeError(
                "index must be FlatVectorIndex"
            )

        payload_writer = BinaryWriter()

        self._write_value(
            payload_writer,
            index.state_dict(),
        )

        payload = (
            payload_writer.to_bytes()
        )

        writer = BinaryWriter()
        writer.write_bytes(
            self.MAGIC
        )
        writer.write_u16(
            self.VERSION
        )
        writer.write_u64(
            fnv1a64(payload)
        )
        writer.write_length_prefixed_bytes(
            payload
        )

        encoded = writer.to_bytes()

        handle = open(
            path,
            "wb",
        )

        try:
            handle.write(
                encoded
            )
        finally:
            handle.close()

        return {
            "path": path,
            "bytes": len(encoded),
            "checksum": fnv1a64(
                encoded
            ),
            "entries": index.count(),
        }

    def load(
        self,
        path,
        metric=None,
    ):
        state = self.read_state(
            path
        )

        index = FlatVectorIndex(
            dimension=int(
                state["dimension"]
            ),
            metric=metric,
        )

        index.load_state_dict(
            state
        )

        return index

    def read_state(self, path):
        if not isinstance(path, str) or path == "":
            raise ValueError(
                "path must be non-empty str"
            )

        handle = open(
            path,
            "rb",
        )

        try:
            encoded = handle.read()
        finally:
            handle.close()

        reader = BinaryReader(
            encoded
        )

        magic = reader.read_bytes(
            len(self.MAGIC)
        )

        if magic != self.MAGIC:
            raise ValueError(
                "invalid vector index magic"
            )

        version = reader.read_u16()

        if version != self.VERSION:
            raise ValueError(
                "unsupported vector index version"
            )

        expected_checksum = (
            reader.read_u64()
        )

        payload = (
            reader.read_length_prefixed_bytes()
        )

        if not reader.eof():
            raise ValueError(
                "unexpected trailing index data"
            )

        actual_checksum = fnv1a64(
            payload
        )

        if (
            actual_checksum
            != expected_checksum
        ):
            raise ValueError(
                "vector index checksum mismatch"
            )

        payload_reader = BinaryReader(
            payload
        )

        state = self._read_value(
            payload_reader
        )

        if not payload_reader.eof():
            raise ValueError(
                "unexpected trailing index payload"
            )

        return state

    def _write_value(
        self,
        writer,
        value,
    ):
        if value is None:
            writer.write_u8(
                self.TAG_NONE
            )
            return

        if value is False:
            writer.write_u8(
                self.TAG_FALSE
            )
            return

        if value is True:
            writer.write_u8(
                self.TAG_TRUE
            )
            return

        if isinstance(value, int):
            writer.write_u8(
                self.TAG_INT
            )
            writer.write_varint(
                value
            )
            return

        if isinstance(value, float):
            writer.write_u8(
                self.TAG_FLOAT
            )
            writer.write_f64(
                value
            )
            return

        if isinstance(value, str):
            writer.write_u8(
                self.TAG_TEXT
            )
            writer.write_text(
                value
            )
            return

        if isinstance(value, (list, tuple)):
            writer.write_u8(
                self.TAG_LIST
            )
            writer.write_varuint(
                len(value)
            )

            for item in value:
                self._write_value(
                    writer,
                    item,
                )

            return

        if isinstance(value, dict):
            writer.write_u8(
                self.TAG_DICT
            )

            keys = []

            for key in value:
                if not isinstance(key, str):
                    raise TypeError(
                        "persistent dict keys must be strings"
                    )

                keys.append(
                    key
                )

            keys.sort()

            writer.write_varuint(
                len(keys)
            )

            for key in keys:
                writer.write_text(
                    key
                )

                self._write_value(
                    writer,
                    value[key],
                )

            return

        raise TypeError(
            "unsupported persistent value type: "
            + type(value).__name__
        )

    def _read_value(
        self,
        reader,
    ):
        tag = reader.read_u8()

        if tag == self.TAG_NONE:
            return None

        if tag == self.TAG_FALSE:
            return False

        if tag == self.TAG_TRUE:
            return True

        if tag == self.TAG_INT:
            return reader.read_varint()

        if tag == self.TAG_FLOAT:
            return reader.read_f64()

        if tag == self.TAG_TEXT:
            return reader.read_text()

        if tag == self.TAG_LIST:
            length = reader.read_varuint()
            result = []
            index = 0

            while index < length:
                result.append(
                    self._read_value(
                        reader
                    )
                )

                index += 1

            return result

        if tag == self.TAG_DICT:
            length = reader.read_varuint()
            result = {}
            index = 0

            while index < length:
                key = reader.read_text()

                result[key] = (
                    self._read_value(
                        reader
                    )
                )

                index += 1

            return result

        raise ValueError(
            "unknown persistent value tag: "
            + str(tag)
        )
