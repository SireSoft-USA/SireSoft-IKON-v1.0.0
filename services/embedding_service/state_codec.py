class EmbeddingStateCodec:
    """
    Deterministic binary persistence for EmbeddingArtifact.
    """

    MAGIC = b"SLLMEMB1"
    FRAME_VERSION = 1

    def encode(
        self,
        artifact,
    ):
        if not isinstance(
            artifact,
            EmbeddingArtifact,
        ):
            raise TypeError(
                "artifact must be EmbeddingArtifact"
            )

        state = artifact.to_dict()
        embedder = state[
            "embedder"
        ]

        idf = embedder[
            "idf_model"
        ]

        payload = BinaryWriter()

        payload.write_text(
            state[
                "tokenizer_signature"
            ]
        )

        payload.write_varuint(
            int(
                embedder[
                    "dimension"
                ]
            )
        )

        payload.write_varuint(
            int(
                embedder[
                    "min_n"
                ]
            )
        )

        payload.write_varuint(
            int(
                embedder[
                    "max_n"
                ]
            )
        )

        payload.write_u8(
            1
            if embedder[
                "use_idf"
            ]
            else 0
        )

        payload.write_u8(
            1
            if embedder[
                "sublinear_tf"
            ]
            else 0
        )

        payload.write_u8(
            1
            if embedder[
                "l2_normalize"
            ]
            else 0
        )

        payload.write_f64(
            float(
                idf[
                    "default_idf"
                ]
            )
        )

        payload.write_varuint(
            int(
                idf[
                    "document_count"
                ]
            )
        )

        frequencies = list(
            idf[
                "document_frequency"
            ]
        )

        payload.write_varuint(
            len(
                frequencies
            )
        )

        for value in frequencies:
            payload.write_varuint(
                int(
                    value
                )
            )

        weights = list(
            idf[
                "idf"
            ]
        )

        payload.write_varuint(
            len(
                weights
            )
        )

        for value in weights:
            payload.write_f64(
                float(
                    value
                )
            )

        payload.write_u8(
            1
            if idf[
                "fitted"
            ]
            else 0
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
                "encoded embedding state must be bytes-like"
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
                "invalid embedding state magic"
            )

        frame_version = (
            reader.read_u16()
        )

        if (
            frame_version
            != self.FRAME_VERSION
        ):
            raise ValueError(
                "unsupported embedding state frame version"
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
                "unexpected trailing embedding state data"
            )

        if (
            fnv1a64(
                payload
            )
            != expected_checksum
        ):
            raise ValueError(
                "embedding state checksum mismatch"
            )

        body = BinaryReader(
            payload
        )

        tokenizer_signature = (
            body.read_text()
        )

        dimension = (
            body.read_varuint()
        )

        min_n = (
            body.read_varuint()
        )

        max_n = (
            body.read_varuint()
        )

        use_idf = (
            body.read_u8()
            == 1
        )

        sublinear_tf = (
            body.read_u8()
            == 1
        )

        l2_normalize = (
            body.read_u8()
            == 1
        )

        default_idf = (
            body.read_f64()
        )

        document_count = (
            body.read_varuint()
        )

        frequency_count = (
            body.read_varuint()
        )

        frequencies = []
        index = 0

        while index < frequency_count:
            frequencies.append(
                body.read_varuint()
            )

            index += 1

        idf_count = (
            body.read_varuint()
        )

        weights = []
        index = 0

        while index < idf_count:
            weights.append(
                body.read_f64()
            )

            index += 1

        fitted = (
            body.read_u8()
            == 1
        )

        if not body.eof():
            raise ValueError(
                "unexpected trailing embedding payload data"
            )

        return EmbeddingArtifact(
            tokenizer_signature=(
                tokenizer_signature
            ),
            embedder_state={
                "type": "HashingTFIDFEmbedder",
                "dimension": dimension,
                "min_n": min_n,
                "max_n": max_n,
                "use_idf": use_idf,
                "sublinear_tf": sublinear_tf,
                "l2_normalize": l2_normalize,
                "idf_model": {
                    "dimension": dimension,
                    "default_idf": default_idf,
                    "document_count": (
                        document_count
                    ),
                    "document_frequency": (
                        frequencies
                    ),
                    "idf": weights,
                    "fitted": fitted,
                },
            },
        )

    def save(
        self,
        path,
        artifact,
    ):
        if not isinstance(
            path,
            str,
        ) or path == "":
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
            encoded = handle.read()
        finally:
            handle.close()

        return self.decode(
            encoded
        )
