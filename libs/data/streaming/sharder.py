class ShardManifestEntry:
    def __init__(
        self,
        shard_index,
        file_path,
        record_count,
        byte_count,
        first_record_index,
        last_record_index,
    ):
        self.shard_index = shard_index
        self.file_path = file_path
        self.record_count = record_count
        self.byte_count = byte_count
        self.first_record_index = first_record_index
        self.last_record_index = last_record_index

    def to_dict(self):
        return {
            "shard_index": self.shard_index,
            "file_path": self.file_path,
            "record_count": self.record_count,
            "byte_count": self.byte_count,
            "first_record_index": self.first_record_index,
            "last_record_index": self.last_record_index,
        }


class TextSharder:
    """
    Splits an incoming stream of records into deterministic shard files.

    This class intentionally does not know about JSON/JSONL/canonical schema.
    The caller provides already-serialized text records, keeping concerns
    separated between serialization and storage.
    """

    def __init__(
        self,
        output_directory,
        prefix="shard",
        extension=".txt",
        max_records=None,
        max_bytes=None,
        encoding="utf-8",
    ):
        if not isinstance(output_directory, str) or output_directory == "":
            raise ValueError("output_directory must be non-empty str")
        if not isinstance(prefix, str) or prefix == "":
            raise ValueError("prefix must be non-empty str")
        if not isinstance(extension, str):
            raise TypeError("extension must be str")
        if max_records is None and max_bytes is None:
            raise ValueError("at least one shard limit must be provided")
        if max_records is not None and (not isinstance(max_records, int) or max_records <= 0):
            raise ValueError("max_records must be positive int or None")
        if max_bytes is not None and (not isinstance(max_bytes, int) or max_bytes <= 0):
            raise ValueError("max_bytes must be positive int or None")

        self.output_directory = output_directory
        self.prefix = prefix
        self.extension = extension
        self.max_records = max_records
        self.max_bytes = max_bytes
        self.encoding = encoding

    def shard_records(self, records, writer_factory):
        """
        records must yield strings. writer_factory(file_path) must return
        a writer object exposing open(), write(), close(), bytes_written().
        """
        manifest = []

        shard_index = -1
        writer = None
        shard_record_count = 0
        shard_first_index = None
        global_index = 0

        try:
            for record in records:
                if not isinstance(record, str):
                    raise TypeError("TextSharder records must be strings")

                record_bytes = len(record.encode(self.encoding))

                must_rotate = False
                if writer is not None:
                    if self.max_records is not None and shard_record_count >= self.max_records:
                        must_rotate = True
                    if (
                        self.max_bytes is not None
                        and shard_record_count > 0
                        and writer.bytes_written() + record_bytes > self.max_bytes
                    ):
                        must_rotate = True

                if writer is None or must_rotate:
                    if writer is not None:
                        manifest.append(
                            ShardManifestEntry(
                                shard_index=shard_index,
                                file_path=current_path,
                                record_count=shard_record_count,
                                byte_count=writer.bytes_written(),
                                first_record_index=shard_first_index,
                                last_record_index=global_index - 1,
                            )
                        )
                        writer.close()

                    shard_index += 1
                    current_path = self._shard_path(shard_index)
                    writer = writer_factory(current_path)
                    writer.open()
                    shard_record_count = 0
                    shard_first_index = global_index

                writer.write(record)
                shard_record_count += 1
                global_index += 1

            if writer is not None:
                manifest.append(
                    ShardManifestEntry(
                        shard_index=shard_index,
                        file_path=current_path,
                        record_count=shard_record_count,
                        byte_count=writer.bytes_written(),
                        first_record_index=shard_first_index,
                        last_record_index=global_index - 1,
                    )
                )
                writer.close()
                writer = None

        finally:
            if writer is not None:
                writer.close()

        return manifest

    def _shard_path(self, shard_index):
        number = str(shard_index)
        while len(number) < 5:
            number = "0" + number

        base = self.output_directory
        if base.endswith("/") or base.endswith("\\"):
            return base + self.prefix + "-" + number + self.extension

        return base + "/" + self.prefix + "-" + number + self.extension
