class TracingPersistence:
    MAGIC = b"SLLMTRC1"
    VERSION = 1

    TAG_NONE = 0
    TAG_FALSE = 1
    TAG_TRUE = 2
    TAG_INT = 3
    TAG_FLOAT = 4
    TAG_TEXT = 5
    TAG_LIST = 6
    TAG_DICT = 7

    def save(
        self,
        path,
        manager,
    ):
        if not isinstance(
            path,
            str,
        ) or path == "":
            raise ValueError(
                "path must be non-empty str"
            )

        state = manager.export_state()

        body_writer = BinaryWriter()

        self._write_value(
            body_writer,
            state,
        )

        payload = (
            body_writer
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
        manager,
    ):
        manager.load_state(
            self.read_state(
                path
            )
        )

        return manager.status()

    def read_state(
        self,
        path,
    ):
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

        if reader.read_bytes(
            len(
                self.MAGIC
            )
        ) != self.MAGIC:
            raise ValueError(
                "invalid tracing snapshot magic"
            )

        version = reader.read_u16()

        if version != self.VERSION:
            raise ValueError(
                "unsupported tracing snapshot version"
            )

        expected = reader.read_u64()

        payload = (
            reader
            .read_length_prefixed_bytes()
        )

        if not reader.eof():
            raise ValueError(
                "unexpected trailing tracing snapshot data"
            )

        if fnv1a64(
            payload
        ) != expected:
            raise ValueError(
                "tracing snapshot checksum mismatch"
            )

        body = BinaryReader(
            payload
        )

        state = self._read_value(
            body
        )

        if not body.eof():
            raise ValueError(
                "unexpected trailing tracing payload"
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
                        "tracing snapshot dictionary keys must be strings"
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
            "unsupported tracing snapshot value type: "
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
            "unknown tracing snapshot tag: "
            + str(
                tag
            )
        )
