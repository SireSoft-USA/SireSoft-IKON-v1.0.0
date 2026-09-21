class TokenizerStateCodec:
    """
    Deterministic binary tokenizer artifact persistence.
    """

    MAGIC = b"SLLMTOK1"
    FRAME_VERSION = 1

    def encode(
        self,
        artifact,
    ):
        if not isinstance(
            artifact,
            TokenizerArtifact,
        ):
            raise TypeError(
                "artifact must be TokenizerArtifact"
            )

        payload = BinaryWriter()

        state = artifact.to_dict()

        payload.write_varuint(
            state["version"]
        )

        payload.write_varuint(
            len(
                state[
                    "special_tokens"
                ]
            )
        )

        for token in state[
            "special_tokens"
        ]:
            payload.write_text(
                token
            )

        payload.write_varuint(
            len(
                state[
                    "merges"
                ]
            )
        )

        for row in state["merges"]:
            payload.write_varuint(
                row["left"]
            )
            payload.write_varuint(
                row["right"]
            )
            payload.write_varuint(
                row["new_id"]
            )

        payload.write_varuint(
            state[
                "target_vocab_size"
            ]
        )

        payload.write_varuint(
            state[
                "min_frequency"
            ]
        )

        raw_payload = (
            payload.to_bytes()
        )

        writer = BinaryWriter()
        writer.write_bytes(
            self.MAGIC
        )
        writer.write_u16(
            self.FRAME_VERSION
        )
        writer.write_u64(
            fnv1a64(
                raw_payload
            )
        )
        writer.write_length_prefixed_bytes(
            raw_payload
        )

        return writer.to_bytes()

    def decode(
        self,
        encoded,
    ):
        if not isinstance(
            encoded,
            (bytes, bytearray),
        ):
            raise TypeError(
                "encoded artifact must be bytes-like"
            )

        reader = BinaryReader(
            bytes(
                encoded
            )
        )

        if reader.read_bytes(
            len(
                self.MAGIC
            )
        ) != self.MAGIC:
            raise ValueError(
                "invalid tokenizer artifact magic"
            )

        frame_version = (
            reader.read_u16()
        )

        if (
            frame_version
            != self.FRAME_VERSION
        ):
            raise ValueError(
                "unsupported tokenizer artifact frame version"
            )

        expected_checksum = (
            reader.read_u64()
        )

        payload = (
            reader
            .read_length_prefixed_bytes()
        )

        if not reader.eof():
            raise ValueError(
                "unexpected trailing tokenizer artifact data"
            )

        if (
            fnv1a64(
                payload
            )
            != expected_checksum
        ):
            raise ValueError(
                "tokenizer artifact checksum mismatch"
            )

        body = BinaryReader(
            payload
        )

        artifact_version = (
            body.read_varuint()
        )

        special_count = (
            body.read_varuint()
        )

        specials = []
        index = 0

        while index < special_count:
            specials.append(
                body.read_text()
            )
            index += 1

        merge_count = (
            body.read_varuint()
        )

        merges = []
        index = 0

        while index < merge_count:
            merges.append({
                "left": body.read_varuint(),
                "right": body.read_varuint(),
                "new_id": body.read_varuint(),
            })

            index += 1

        target_vocab_size = (
            body.read_varuint()
        )

        min_frequency = (
            body.read_varuint()
        )

        if not body.eof():
            raise ValueError(
                "unexpected tokenizer artifact payload data"
            )

        return TokenizerArtifact.from_dict({
            "version": artifact_version,
            "special_tokens": specials,
            "merges": merges,
            "target_vocab_size": (
                target_vocab_size
            ),
            "min_frequency": (
                min_frequency
            ),
        })

    def save(
        self,
        path,
        artifact,
    ):
        if not isinstance(path, str) or path == "":
            raise ValueError(
                "path must be non-empty str"
            )

        encoded = self.encode(
            artifact
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
            "checksum": fnv1a64(
                encoded
            ),
        }

    def load(
        self,
        path,
    ):
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

        return self.decode(
            encoded
        )
