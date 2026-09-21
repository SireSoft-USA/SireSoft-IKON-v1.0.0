class RawDatasetInspector:
    """
    Lightweight raw-file inspector.

    It intentionally does not preprocess or normalize datasets. That belongs to
    preprocessing_service. This layer only verifies declaration, readability,
    format sanity, size and a streaming FNV-1a fingerprint.
    """

    FNV_OFFSET = 0xCBF29CE484222325
    FNV_PRIME = 0x100000001B3
    MASK = 0xFFFFFFFFFFFFFFFF

    def __init__(
        self,
        chunk_size=65536,
        sample_size=65536,
    ):
        if not isinstance(chunk_size, int) or chunk_size <= 0:
            raise ValueError(
                "chunk_size must be positive int"
            )

        if not isinstance(sample_size, int) or sample_size <= 0:
            raise ValueError(
                "sample_size must be positive int"
            )

        self.chunk_size = chunk_size
        self.sample_size = sample_size

    def inspect_manifest(
        self,
        manifest,
    ):
        if not isinstance(manifest, DatasetManifest):
            raise TypeError(
                "manifest must be DatasetManifest"
            )

        snapshots = []

        for source in manifest.sources:
            snapshots.append(
                self.inspect_source(
                    source
                )
            )

        return DatasetSnapshot(
            dataset_id=manifest.dataset_id,
            files=snapshots,
        )

    def inspect_source(
        self,
        source,
    ):
        if not isinstance(source, DatasetSource):
            raise TypeError(
                "source must be DatasetSource"
            )

        try:
            handle = open(
                source.path,
                "rb",
            )

        except FileNotFoundError:
            return RawFileSnapshot(
                path=source.path,
                source_format=source.source_format,
                role=source.role,
                required=source.required,
                exists=False,
                error="file_not_found",
            )

        checksum = self.FNV_OFFSET
        size = 0
        first_sample = b""
        last_sample = b""

        try:
            while True:
                block = handle.read(
                    self.chunk_size
                )

                if block == b"":
                    break

                if first_sample == b"":
                    first_sample = block[
                        :self.sample_size
                    ]

                size += len(block)
                last_sample = block[
                    -self.sample_size:
                ]

                for byte_value in block:
                    checksum ^= byte_value
                    checksum = (
                        checksum
                        * self.FNV_PRIME
                    ) & self.MASK

        finally:
            handle.close()

        sanity_ok, error = (
            self._format_sanity(
                source.source_format,
                first_sample,
                last_sample,
                size,
            )
        )

        return RawFileSnapshot(
            path=source.path,
            source_format=source.source_format,
            role=source.role,
            required=source.required,
            exists=True,
            size_bytes=size,
            checksum=self._hex64(
                checksum
            ),
            sanity_ok=sanity_ok,
            error=error,
        )

    def _format_sanity(
        self,
        source_format,
        first_sample,
        last_sample,
        size,
    ):
        if size == 0:
            return (
                False,
                "empty_file",
            )

        if source_format == "gzip":
            if (
                len(first_sample) >= 2
                and first_sample[0] == 0x1F
                and first_sample[1] == 0x8B
            ):
                return (
                    True,
                    None,
                )

            return (
                False,
                "invalid_gzip_magic",
            )

        try:
            first_text = first_sample.decode(
                "utf-8"
            )

            last_text = last_sample.decode(
                "utf-8"
            )

        except UnicodeDecodeError:
            return (
                False,
                "invalid_utf8",
            )

        if source_format == "text":
            return (
                True,
                None,
            )

        if source_format == "json":
            first = self._first_non_space(
                first_text
            )

            last = self._last_non_space(
                last_text
            )

            if first not in (
                "{",
                "[",
            ):
                return (
                    False,
                    "json_invalid_start",
                )

            if last not in (
                "}",
                "]",
            ):
                return (
                    False,
                    "json_invalid_end",
                )

            return (
                True,
                None,
            )

        if source_format == "jsonl":
            first_line = self._first_nonempty_line(
                first_text
            )

            if first_line is None:
                return (
                    False,
                    "jsonl_no_record",
                )

            stripped = first_line.strip()

            if (
                not stripped.startswith("{")
                or not stripped.endswith("}")
            ):
                return (
                    False,
                    "jsonl_first_record_not_object"
                )

            return (
                True,
                None,
            )

        return (
            False,
            "unsupported_format",
        )

    def _first_non_space(
        self,
        text,
    ):
        for char in text:
            if char not in (
                " ",
                "\t",
                "\r",
                "\n",
            ):
                return char

        return None

    def _last_non_space(
        self,
        text,
    ):
        index = len(text) - 1

        while index >= 0:
            char = text[index]

            if char not in (
                " ",
                "\t",
                "\r",
                "\n",
            ):
                return char

            index -= 1

        return None

    def _first_nonempty_line(
        self,
        text,
    ):
        lines = text.splitlines()

        for line in lines:
            if line.strip() != "":
                return line

        # If sample contains a complete one-line JSON object without newline,
        # splitlines() still returns it.
        return None

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

            nibble = (
                value >> shift
            ) & 0xF

            result += digits[
                nibble
            ]

            index += 1

        return result
