class CheckpointCodec:
    """
    Deterministic recursive checkpoint codec using SireLLM BinaryWriter/Reader.

    Supported state types:
      None, bool, int, float, str, bytes, list, tuple, dict[str, ...]

    No pickle/json/third-party serialization is used.
    """

    TAG_NONE = 0
    TAG_FALSE = 1
    TAG_TRUE = 2
    TAG_INT = 3
    TAG_FLOAT = 4
    TAG_TEXT = 5
    TAG_BYTES = 6
    TAG_LIST = 7
    TAG_TUPLE = 8
    TAG_DICT = 9

    MAGIC = b"SLLMCKP1"
    VERSION = 1

    def encode(self, value):
        payload_writer = BinaryWriter()
        self._write_value(
            payload_writer,
            value,
        )
        payload = payload_writer.to_bytes()

        writer = BinaryWriter()
        writer.write_bytes(self.MAGIC)
        writer.write_u16(self.VERSION)
        writer.write_u64(
            fnv1a64(payload)
        )
        writer.write_length_prefixed_bytes(
            payload
        )

        return writer.to_bytes()

    def decode(self, data):
        reader = BinaryReader(data)

        magic = reader.read_bytes(
            len(self.MAGIC)
        )

        if magic != self.MAGIC:
            raise ValueError(
                "invalid SireLLM checkpoint magic"
            )

        version = reader.read_u16()

        if version != self.VERSION:
            raise ValueError(
                "unsupported checkpoint version"
            )

        expected_checksum = (
            reader.read_u64()
        )

        payload = (
            reader.read_length_prefixed_bytes()
        )

        actual_checksum = fnv1a64(
            payload
        )

        if actual_checksum != expected_checksum:
            raise ValueError(
                "checkpoint checksum mismatch"
            )

        if not reader.eof():
            raise ValueError(
                "unexpected trailing checkpoint data"
            )

        payload_reader = BinaryReader(
            payload
        )

        value = self._read_value(
            payload_reader
        )

        if not payload_reader.eof():
            raise ValueError(
                "unexpected trailing payload data"
            )

        return value

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

        if isinstance(value, list):
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

        if isinstance(value, tuple):
            writer.write_u8(
                self.TAG_TUPLE
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
                        "checkpoint dict keys must be strings"
                    )

                keys.append(key)

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
            "unsupported checkpoint value type: "
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
            return (
                reader.read_length_prefixed_bytes()
            )

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

        if tag == self.TAG_TUPLE:
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

            return tuple(result)

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
            "unknown checkpoint type tag: "
            + str(tag)
        )


class CheckpointManager:
    """
    Saves/restores a complete trainable SireLLM state:
      model parameters
      optimizer moments/step
      scheduler state
      trainer counters
      user metadata
    """

    def __init__(self, codec=None):
        self.codec = (
            CheckpointCodec()
            if codec is None
            else codec
        )

    def create_payload(
        self,
        model,
        optimizer=None,
        scheduler=None,
        trainer=None,
        metadata=None,
    ):
        if model is None or not hasattr(
            model,
            "state_dict",
        ):
            raise TypeError(
                "model must provide state_dict()"
            )

        if metadata is not None and not isinstance(
            metadata,
            dict,
        ):
            raise TypeError(
                "metadata must be dict or None"
            )

        payload = {
            "format": "SireLLMCheckpoint",
            "version": 1,
            "model": model.state_dict(),
            "optimizer": None,
            "scheduler": None,
            "trainer": None,
            "metadata": (
                {}
                if metadata is None
                else dict(metadata)
            ),
        }

        if optimizer is not None:
            if not hasattr(
                optimizer,
                "state_dict",
            ):
                raise TypeError(
                    "optimizer must provide state_dict()"
                )

            payload["optimizer"] = (
                optimizer.state_dict()
            )

        if scheduler is not None:
            if not hasattr(
                scheduler,
                "state_dict",
            ):
                raise TypeError(
                    "scheduler must provide state_dict()"
                )

            payload["scheduler"] = (
                scheduler.state_dict()
            )

        if trainer is not None:
            if not hasattr(
                trainer,
                "state_dict",
            ):
                raise TypeError(
                    "trainer must provide state_dict()"
                )

            payload["trainer"] = (
                trainer.state_dict()
            )

        return payload

    def save(
        self,
        path,
        model,
        optimizer=None,
        scheduler=None,
        trainer=None,
        metadata=None,
    ):
        if not isinstance(path, str) or path == "":
            raise ValueError(
                "checkpoint path must be non-empty str"
            )

        payload = self.create_payload(
            model=model,
            optimizer=optimizer,
            scheduler=scheduler,
            trainer=trainer,
            metadata=metadata,
        )

        encoded = self.codec.encode(
            payload
        )

        handle = open(
            path,
            "wb",
        )

        try:
            handle.write(encoded)
        finally:
            handle.close()

        return {
            "path": path,
            "bytes": len(encoded),
            "checksum": fnv1a64(encoded),
        }

    def read_payload(self, path):
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

        return self.codec.decode(
            data
        )

    def load(
        self,
        path,
        model,
        optimizer=None,
        scheduler=None,
        trainer=None,
        strict_model=True,
    ):
        payload = self.read_payload(
            path
        )

        if payload.get("format") != "SireLLMCheckpoint":
            raise ValueError(
                "not a SireLLM checkpoint payload"
            )

        model.load_state_dict(
            payload["model"],
            strict=strict_model,
        )

        optimizer_state = payload.get(
            "optimizer"
        )

        if (
            optimizer is not None
            and optimizer_state is not None
        ):
            self._restore_optimizer_config(
                optimizer,
                optimizer_state,
            )

            optimizer.load_state_dict(
                optimizer_state
            )

        scheduler_state = payload.get(
            "scheduler"
        )

        if (
            scheduler is not None
            and scheduler_state is not None
        ):
            if not hasattr(
                scheduler,
                "load_state_dict",
            ):
                raise TypeError(
                    "scheduler must provide load_state_dict()"
                )

            scheduler.load_state_dict(
                scheduler_state
            )

        trainer_state = payload.get(
            "trainer"
        )

        if (
            trainer is not None
            and trainer_state is not None
        ):
            trainer.load_state_dict(
                trainer_state
            )

        return payload

    def _restore_optimizer_config(
        self,
        optimizer,
        state,
    ):
        names = (
            "learning_rate",
            "momentum",
            "dampening",
            "weight_decay",
            "nesterov",
            "beta1",
            "beta2",
            "epsilon",
            "max_grad_norm",
        )

        for name in names:
            if (
                name in state
                and hasattr(
                    optimizer,
                    name,
                )
            ):
                setattr(
                    optimizer,
                    name,
                    state[name],
                )
