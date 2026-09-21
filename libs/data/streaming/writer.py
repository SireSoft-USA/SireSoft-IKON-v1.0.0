class StreamWriter:
    """
    Dependency-free streaming writer.

    Supports deterministic text/binary writes and explicit flush behavior.
    """

    def __init__(
        self,
        file_path,
        mode="text",
        encoding="utf-8",
        append=False,
        flush_threshold=65536,
    ):
        if not isinstance(file_path, str) or file_path == "":
            raise ValueError("file_path must be non-empty str")
        if mode not in ("text", "binary"):
            raise ValueError("mode must be 'text' or 'binary'")
        if not isinstance(flush_threshold, int) or flush_threshold <= 0:
            raise ValueError("flush_threshold must be positive int")

        self.file_path = file_path
        self.mode = mode
        self.encoding = encoding
        self.append = append
        self.flush_threshold = flush_threshold

        self._handle = None
        self._opened = False
        self._bytes_written = 0
        self._since_flush = 0

    def open(self):
        if self._opened:
            return self

        if self.mode == "binary":
            file_mode = "ab" if self.append else "wb"
            self._handle = open(self.file_path, file_mode)
        else:
            file_mode = "a" if self.append else "w"
            self._handle = open(
                self.file_path,
                file_mode,
                encoding=self.encoding,
                newline="",
            )

        self._opened = True
        return self

    def close(self):
        if self._handle is not None:
            self._handle.flush()
            self._handle.close()
        self._handle = None
        self._opened = False

    def __enter__(self):
        return self.open()

    def __exit__(self, exc_type, exc_value, traceback):
        self.close()
        return False

    def is_open(self):
        return self._opened

    def bytes_written(self):
        return self._bytes_written

    def tell(self):
        if not self._opened:
            raise RuntimeError("writer is not open")
        return self._handle.tell()

    def flush(self):
        if not self._opened:
            raise RuntimeError("writer is not open")
        self._handle.flush()
        self._since_flush = 0

    def write(self, data):
        if not self._opened:
            raise RuntimeError("writer is not open")

        if self.mode == "binary":
            if not isinstance(data, (bytes, bytearray)):
                raise TypeError("binary writer requires bytes or bytearray")
            payload = bytes(data)
            self._handle.write(payload)
            byte_count = len(payload)
        else:
            if not isinstance(data, str):
                raise TypeError("text writer requires str")
            self._handle.write(data)
            byte_count = len(data.encode(self.encoding))

        self._bytes_written += byte_count
        self._since_flush += byte_count

        if self._since_flush >= self.flush_threshold:
            self.flush()

        return byte_count

    def write_line(self, text, ending="\n"):
        if self.mode != "text":
            raise RuntimeError("write_line is only available in text mode")
        if not isinstance(text, str):
            raise TypeError("text must be str")
        if not isinstance(ending, str):
            raise TypeError("ending must be str")
        return self.write(text + ending)

    def write_many(self, iterable):
        total = 0
        for item in iterable:
            total += self.write(item)
        return total
