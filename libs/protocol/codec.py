class ProtocolCodec:
    """
    Deterministic binary protocol framing using SireLLM core serialization.

    Frame:
      magic
      frame_version
      checksum(payload)
      payload_length + payload

    Payload is recursively encoded without pickle/json/struct.
    """

    MAGIC = b"SLLMPROT"
    FRAME_VERSION = 1

    TAG_NONE = 0
    TAG_FALSE = 1
    TAG_TRUE = 2
    TAG_INT = 3
    TAG_FLOAT = 4
    TAG_TEXT = 5
    TAG_BYTES = 6
    TAG_LIST = 7
    TAG_DICT = 8

    def __init__(
        self,
        max_frame_bytes=8 * 1024 * 1024,
        validator=None,
    ):
        if not isinstance(max_frame_bytes, int) or max_frame_bytes <= 0:
            raise ValueError("max_frame_bytes must be positive int")

        self.max_frame_bytes = max_frame_bytes
        self.validator = (
            ProtocolValidator()
            if validator is None
            else validator
        )

    def encode_message(self, message):
        self.validator.require_valid_message(
            message
        )

        payload_writer = BinaryWriter()

        self._write_value(
            payload_writer,
            message.to_dict(),
        )

        payload = payload_writer.to_bytes()

        writer = BinaryWriter()
        writer.write_bytes(
            self.MAGIC
        )
        writer.write_u16(
            self.FRAME_VERSION
        )
        writer.write_u64(
            fnv1a64(payload)
        )
        writer.write_length_prefixed_bytes(
            payload
        )

        encoded = writer.to_bytes()

        if len(encoded) > self.max_frame_bytes:
            raise ValueError(
                "encoded frame exceeds max_frame_bytes"
            )

        return encoded

    def decode_message(self, encoded):
        if not isinstance(
            encoded,
            (bytes, bytearray),
        ):
            raise TypeError(
                "encoded frame must be bytes-like"
            )

        if len(encoded) > self.max_frame_bytes:
            raise ValueError(
                "encoded frame exceeds max_frame_bytes"
            )

        reader = BinaryReader(
            bytes(encoded)
        )

        magic = reader.read_bytes(
            len(self.MAGIC)
        )

        if magic != self.MAGIC:
            raise ValueError(
                "invalid protocol frame magic"
            )

        frame_version = reader.read_u16()

        if frame_version != self.FRAME_VERSION:
            raise ValueError(
                "unsupported frame version"
            )

        expected_checksum = (
            reader.read_u64()
        )

        payload = (
            reader.read_length_prefixed_bytes()
        )

        if not reader.eof():
            raise ValueError(
                "unexpected trailing protocol data"
            )

        actual_checksum = fnv1a64(
            payload
        )

        if actual_checksum != expected_checksum:
            raise ValueError(
                "protocol checksum mismatch"
            )

        payload_reader = BinaryReader(
            payload
        )

        value = self._read_value(
            payload_reader
        )

        if not payload_reader.eof():
            raise ValueError(
                "unexpected trailing protocol payload"
            )

        message = ProtocolMessage.from_dict(
            value
        )

        self.validator.require_valid_message(
            message
        )

        return message

    def encode_request(self, request):
        if not isinstance(request, ServiceRequest):
            raise TypeError("request must be ServiceRequest")

        errors = self.validator.validate_request(
            request
        )

        if len(errors) > 0:
            raise ValueError(
                "invalid service request: "
                + "; ".join(errors)
            )

        return self.encode_message(
            request.to_message()
        )

    def decode_request(self, encoded):
        return ServiceRequest.from_message(
            self.decode_message(
                encoded
            )
        )

    def encode_response(self, response):
        if not isinstance(response, ServiceResponse):
            raise TypeError("response must be ServiceResponse")

        errors = self.validator.validate_response(
            response
        )

        if len(errors) > 0:
            raise ValueError(
                "invalid service response: "
                + "; ".join(errors)
            )

        return self.encode_message(
            response.to_message()
        )

    def decode_response(self, encoded):
        return ServiceResponse.from_message(
            self.decode_message(
                encoded
            )
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

        if isinstance(
            value,
            (bytes, bytearray),
        ):
            writer.write_u8(
                self.TAG_BYTES
            )
            writer.write_length_prefixed_bytes(
                bytes(value)
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
                        "protocol dict keys must be strings"
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
            "unsupported protocol value type: "
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

        if tag == self.TAG_BYTES:
            return reader.read_length_prefixed_bytes()

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
            "unknown protocol payload tag: "
            + str(tag)
        )
