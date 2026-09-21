class SplitResult:
    def __init__(self):
        self.train = []
        self.validation = []
        self.test = []

    def total_count(self):
        return len(self.train) + len(self.validation) + len(self.test)

    def counts(self):
        return {
            "train": len(self.train),
            "validation": len(self.validation),
            "test": len(self.test),
        }


class CorpusSplitter:
    """
    Deterministic train/validation/test splitter.

    Instead of random.shuffle, each document is assigned by a stable handwritten
    FNV-1a hash. The same corpus and seed produce the same split on every run.

    group_key can be used to prevent leakage: e.g. all messages from the same
    conversation/tree can be forced into the same split.
    """

    def __init__(
        self,
        train_ratio=0.90,
        validation_ratio=0.05,
        test_ratio=0.05,
        seed="sirellm-v1",
    ):
        self._validate_ratios(train_ratio, validation_ratio, test_ratio)

        if not isinstance(seed, str):
            raise TypeError("seed must be str")

        self.train_ratio = train_ratio
        self.validation_ratio = validation_ratio
        self.test_ratio = test_ratio
        self.seed = seed

    def split(self, documents, group_key=None, mutate_documents=True):
        result = SplitResult()

        for document in documents:
            if not hasattr(document, "document_id"):
                raise TypeError("document must provide document_id")

            key = document.document_id

            if group_key is not None:
                if not callable(group_key):
                    raise TypeError("group_key must be callable or None")
                grouped = group_key(document)
                if grouped is not None:
                    key = str(grouped)

            split_name = self.assignment_for_key(key)

            if mutate_documents and hasattr(document, "set_split"):
                document.set_split(split_name)
            elif mutate_documents and hasattr(document, "split"):
                document.split = split_name

            if split_name == "train":
                result.train.append(document)
            elif split_name == "validation":
                result.validation.append(document)
            else:
                result.test.append(document)

        return result

    def assignment_for_key(self, key):
        if not isinstance(key, str):
            key = str(key)

        value = self._fnv1a64(self.seed + "|" + key)

        # Convert into deterministic [0,1) using 1,000,000 buckets.
        bucket = value % 1000000
        fraction = bucket / 1000000.0

        train_cut = self.train_ratio
        validation_cut = self.train_ratio + self.validation_ratio

        if fraction < train_cut:
            return "train"

        if fraction < validation_cut:
            return "validation"

        return "test"

    def _validate_ratios(self, train, validation, test):
        values = (train, validation, test)

        for value in values:
            if not isinstance(value, (int, float)):
                raise TypeError("split ratios must be numeric")
            if value < 0.0 or value > 1.0:
                raise ValueError("split ratios must be between 0 and 1")

        total = train + validation + test
        difference = total - 1.0
        if difference < 0:
            difference = -difference

        if difference > 0.0000001:
            raise ValueError("split ratios must sum to 1.0")

    def _fnv1a64(self, text):
        data = self._utf8_bytes(text)
        value = 0xCBF29CE484222325

        i = 0
        while i < len(data):
            value ^= data[i]
            value = (value * 0x100000001B3) & 0xFFFFFFFFFFFFFFFF
            i += 1

        return value

    def _utf8_bytes(self, text):
        values = []

        for char in text:
            cp = ord(char)

            if cp <= 0x7F:
                values.append(cp)
            elif cp <= 0x7FF:
                values.append(0xC0 | (cp >> 6))
                values.append(0x80 | (cp & 0x3F))
            elif cp <= 0xFFFF:
                if 0xD800 <= cp <= 0xDFFF:
                    raise ValueError("isolated surrogate")
                values.append(0xE0 | (cp >> 12))
                values.append(0x80 | ((cp >> 6) & 0x3F))
                values.append(0x80 | (cp & 0x3F))
            else:
                values.append(0xF0 | (cp >> 18))
                values.append(0x80 | ((cp >> 12) & 0x3F))
                values.append(0x80 | ((cp >> 6) & 0x3F))
                values.append(0x80 | (cp & 0x3F))

        return values
