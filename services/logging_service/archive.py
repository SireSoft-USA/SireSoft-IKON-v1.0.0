class LogArchive:
    """
    Checksum-protected deterministic binary archive for log records.
    """

    MAGIC = b"SLLMLOG1"
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
        records,
    ):
        if not isinstance(
            path,
            str,
        ) or path == "":
            raise ValueError(
                "path must be non-empty str"
            )

        state = [
            record.to_dict()
            for record in records
        ]

        payload_writer = (
            BinaryWriter()
        )

        self._write_value(
            payload_writer,
            state,
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

        encoded = (
            writer.to_bytes()
        )

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
            "records": len(
                state
            ),
            "checksum": fnv1a64(
                encoded
            ),
        }

    def load(
        self,
        path,
    ):
        rows = self.read_state(
            path
        )

        return [
            LogRecord.from_dict(
                row
            )
            for row in rows
        ]

    def read_state(
        self,
        path,
    ):
        if not isinstance(
            path,
            str,
        ) or path == "":
            raise ValueError(
                "path must be non-empty str"
            )

        handle = open(
            path,
            "rb",
        )

        try:
            encoded = (
                handle.read()
            )
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
                "invalid log archive magic"
            )

        version = (
            reader.read_u16()
        )

        if version != self.VERSION:
            raise ValueError(
                "unsupported log archive version"
            )

        expected = (
            reader.read_u64()
        )

        payload = (
            reader
            .read_length_prefixed_bytes()
        )

        if not reader.eof():
            raise ValueError(
                "unexpected trailing log archive data"
            )

        if (
            fnv1a64(
                payload
            )
            != expected
        ):
            raise ValueError(
                "log archive checksum mismatch"
            )

        payload_reader = (
            BinaryReader(
                payload
            )
        )

        state = self._read_value(
            payload_reader
        )

        if not payload_reader.eof():
            raise ValueError(
                "unexpected trailing log payload data"
            )

        if not isinstance(
            state,
            list,
        ):
            raise ValueError(
                "log archive payload must be list"
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
                        "log archive dictionary keys must be strings"
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
            "unsupported log archive value type: "
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
            "unknown log archive tag: "
            + str(
                tag
            )
        )
