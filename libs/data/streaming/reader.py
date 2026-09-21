class StreamReader:
    """
    Dependency-free streaming reader for large dataset files.

    Goals:
    - never require loading an entire dataset into memory
    - support text and binary reading
    - preserve exact source bytes/text
    - expose deterministic chunk iteration
    """

    def __init__(self, file_path, mode="text", encoding="utf-8", chunk_size=65536):
        if not isinstance(file_path, str) or file_path == "":
            raise ValueError("file_path must be non-empty str")
        if mode not in ("text", "binary"):
            raise ValueError("mode must be 'text' or 'binary'")
        if not isinstance(chunk_size, int) or chunk_size <= 0:
            raise ValueError("chunk_size must be positive int")

        self.file_path = file_path
        self.mode = mode
        self.encoding = encoding
        self.chunk_size = chunk_size
        self._handle = None
        self._opened = False
        self._line_number = 0
        self._bytes_read = 0

    def open(self):
        if self._opened:
            return self
        if self.mode == "binary":
            self._handle = open(self.file_path, "rb")
        else:
            self._handle = open(self.file_path, "r", encoding=self.encoding, newline="")
        self._opened = True
        return self

    def close(self):
        if self._handle is not None:
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

    def tell(self):
        if not self._opened:
            raise RuntimeError("reader is not open")
        return self._handle.tell()

    def seek(self, offset):
        if not self._opened:
            raise RuntimeError("reader is not open")
        if not isinstance(offset, int) or offset < 0:
            raise ValueError("offset must be non-negative int")
        self._handle.seek(offset)
        self._line_number = 0

    def bytes_read(self):
        return self._bytes_read

    def line_number(self):
        return self._line_number

    def read_chunk(self, size=None):
        if not self._opened:
            raise RuntimeError("reader is not open")

        if size is None:
            size = self.chunk_size
        if not isinstance(size, int) or size <= 0:
            raise ValueError("size must be positive int")

        data = self._handle.read(size)

        if self.mode == "binary":
            self._bytes_read += len(data)
        else:
            self._bytes_read += len(data.encode(self.encoding))

        return data

    def iter_chunks(self, size=None):
        if not self._opened:
            self.open()

        while True:
            chunk = self.read_chunk(size)
            if chunk == b"" or chunk == "":
                break
            yield chunk

    def read_line(self, keep_ending=True):
        if not self._opened:
            raise RuntimeError("reader is not open")
        if self.mode != "text":
            raise RuntimeError("read_line is only available in text mode")

        line = self._handle.readline()
        if line == "":
            return None

        self._line_number += 1
        self._bytes_read += len(line.encode(self.encoding))

        if keep_ending:
            return line

        if line.endswith("\r\n"):
            return line[:-2]
        if line.endswith("\n") or line.endswith("\r"):
            return line[:-1]
        return line

    def iter_lines(self, keep_ending=True, skip_blank=False):
        if self.mode != "text":
            raise RuntimeError("iter_lines is only available in text mode")
        if not self._opened:
            self.open()

        while True:
            line = self.read_line(keep_ending=keep_ending)
            if line is None:
                break

            if skip_blank:
                candidate = line
                if keep_ending:
                    candidate = candidate.rstrip("\r\n")
                if candidate.strip() == "":
                    continue

            yield line

    def read_all(self):
        if not self._opened:
            raise RuntimeError("reader is not open")

        parts = []
        for chunk in self.iter_chunks():
            parts.append(chunk)

        if self.mode == "binary":
            return b"".join(parts)
        return "".join(parts)
