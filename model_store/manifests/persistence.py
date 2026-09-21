class ManifestPersistence:
    """
    Deterministic checksum-protected manifest codec.
    """

    MAGIC = b"SLLMMNF1"
    VERSION = 1

    TAG_NONE = 0
    TAG_FALSE = 1
    TAG_TRUE = 2
    TAG_INT = 3
    TAG_FLOAT = 4
    TAG_TEXT = 5
    TAG_LIST = 6
    TAG_DICT = 7

    def encode(
        self,
        manifest,
    ):
        if not isinstance(
            manifest,
            ModelManifest,
        ):
            raise TypeError(
                "manifest must be ModelManifest"
            )

        payload_writer = (
            BinaryWriter()
        )

        self._write_value(
            payload_writer,
            manifest.to_dict(),
        )

        payload = (
            payload_writer
            .to_bytes()
        )

        writer = BinaryWriter()

        writer.write_bytes(
            self.MAGIC
        )
        writer.write_u16(
            self.VERSION
        )
        writer.write_u64(
            fnv1a64(
                payload
            )
        )
        writer.write_length_prefixed_bytes(
            payload
        )

        return writer.to_bytes()

    def decode(
        self,
        data,
    ):
        reader = BinaryReader(
            data
        )

        if reader.read_bytes(
            len(
                self.MAGIC
            )
        ) != self.MAGIC:
            raise ValueError(
                "invalid model manifest magic"
            )

        version = reader.read_u16()

        if version != self.VERSION:
            raise ValueError(
                "unsupported model manifest file version"
            )

        expected = reader.read_u64()

        payload = (
            reader
            .read_length_prefixed_bytes()
        )

        if not reader.eof():
            raise ValueError(
                "unexpected trailing model manifest data"
            )

        if fnv1a64(
            payload
        ) != expected:
            raise ValueError(
                "model manifest checksum mismatch"
            )

        body = BinaryReader(
            payload
        )

        state = self._read_value(
            body
        )

        if not body.eof():
            raise ValueError(
                "unexpected trailing model manifest payload"
            )

        return ModelManifest.from_dict(
            state
        )

    def save(
        self,
        path,
        manifest,
    ):
        encoded = self.encode(
            manifest
        )

        handle = open(
            path,
            "xb",
        )

        try:
            handle.write(
                encoded
            )
        finally:
            handle.close()

        return {
            "path": path,
            "bytes": len(
                encoded
            ),
            "checksum": fnv1a64(
                encoded
            ),
        }

    def load(
        self,
        path,
    ):
        handle = open(
            path,
            "rb",
        )

        try:
            data = handle.read()
        finally:
            handle.close()

        return self.decode(
            data
        )

    def file_checksum(
        self,
        path,
    ):
        handle = open(
            path,
            "rb",
        )

        try:
            data = handle.read()
        finally:
            handle.close()

        return fnv1a64(
            data
        )

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

        if isinstance(
            value,
            int,
        ):
            writer.write_u8(
                self.TAG_INT
            )
            writer.write_varint(
                value
            )
            return

        if isinstance(
            value,
            float,
        ):
            writer.write_u8(
                self.TAG_FLOAT
            )
            writer.write_f64(
                value
            )
            return

        if isinstance(
            value,
            str,
        ):
            writer.write_u8(
                self.TAG_TEXT
            )
            writer.write_text(
                value
            )
            return

        if isinstance(
            value,
            (list, tuple),
        ):
            writer.write_u8(
                self.TAG_LIST
            )
            writer.write_varuint(
                len(
                    value
                )
            )

            for item in value:
                self._write_value(
                    writer,
                    item,
                )

            return

        if isinstance(
            value,
            dict,
        ):
            keys = []

            for key in value:
                if not isinstance(
                    key,
                    str,
                ):
                    raise TypeError(
                        "manifest dictionary keys must be strings"
                    )

                keys.append(
                    key
                )

            keys.sort()

            writer.write_u8(
                self.TAG_DICT
            )
            writer.write_varuint(
                len(
                    keys
                )
            )

            for key in keys:
                writer.write_text(
                    key
                )

                self._write_value(
                    writer,
                    value[
                        key
                    ],
                )

            return

        raise TypeError(
            "unsupported manifest value type: "
            + type(
                value
            ).__name__
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
            length = (
                reader.read_varuint()
            )

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
            length = (
                reader.read_varuint()
            )

            result = {}
            index = 0

            while index < length:
                key = reader.read_text()

                result[
                    key
                ] = self._read_value(
                    reader
                )

                index += 1

            return result

        raise ValueError(
            "unknown manifest value tag: "
            + str(
                tag
            )
        )
