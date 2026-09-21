class BoundaryDetector:
    """
    Conservative paragraph/sentence boundary detector using exact offsets.
    """

    SENTENCE_ENDINGS = (
        ".",
        "!",
        "?",
        "؟",
        "。",
        "！",
        "？",
    )

    CLOSERS = (
        '"',
        "'",
        "”",
        "’",
        ")",
        "]",
        "}",
    )

    def paragraph_ends(self, text):
        self._validate_text(text)

        ends = []
        index = 0

        while index < len(text):
            if text[index] == "\n":
                cursor = index

                while (
                    cursor < len(text)
                    and text[cursor] == "\n"
                ):
                    cursor += 1

                if cursor - index >= 2:
                    ends.append(cursor)

                index = cursor
            else:
                index += 1

        if len(text) > 0 and (
            len(ends) == 0
            or ends[-1] != len(text)
        ):
            ends.append(len(text))

        return self._deduplicate_sorted(ends)

    def sentence_ends(self, text):
        self._validate_text(text)

        ends = []
        index = 0

        while index < len(text):
            char = text[index]

            if char in self.SENTENCE_ENDINGS:
                if (
                    char == "."
                    and index > 0
                    and index + 1 < len(text)
                    and self._is_digit(text[index - 1])
                    and self._is_digit(text[index + 1])
                ):
                    index += 1
                    continue

                cursor = index + 1

                while (
                    cursor < len(text)
                    and text[cursor] in self.SENTENCE_ENDINGS
                ):
                    cursor += 1

                while (
                    cursor < len(text)
                    and text[cursor] in self.CLOSERS
                ):
                    cursor += 1

                while (
                    cursor < len(text)
                    and text[cursor] in (" ", "\t")
                ):
                    cursor += 1

                ends.append(cursor)
                index = cursor
                continue

            if char == "\n":
                ends.append(index + 1)

            index += 1

        if len(text) > 0 and (
            len(ends) == 0
            or ends[-1] != len(text)
        ):
            ends.append(len(text))

        return self._deduplicate_sorted(ends)

    def preferred_ends(self, text):
        merged = []

        for value in self.paragraph_ends(text):
            merged.append(value)

        for value in self.sentence_ends(text):
            merged.append(value)

        return self._deduplicate_sorted(merged)

    def best_end(self, text, start, hard_end, minimum_end=None):
        self._validate_text(text)

        if not isinstance(start, int) or start < 0:
            raise ValueError("start must be non-negative int")

        if not isinstance(hard_end, int) or hard_end < start:
            raise ValueError("hard_end must be int >= start")

        if hard_end > len(text):
            hard_end = len(text)

        if minimum_end is None:
            minimum_end = start

        if minimum_end < start:
            minimum_end = start

        candidates = self.preferred_ends(
            text[start:hard_end]
        )

        best = None

        for relative_end in candidates:
            absolute_end = start + relative_end

            if (
                absolute_end <= hard_end
                and absolute_end >= minimum_end
            ):
                if best is None or absolute_end > best:
                    best = absolute_end

        if best is None:
            return hard_end

        return best

    def _is_digit(self, char):
        return "0" <= char <= "9"

    def _validate_text(self, text):
        if not isinstance(text, str):
            raise TypeError("text must be str")

    def _deduplicate_sorted(self, values):
        ordered = sorted(values)
        result = []
        previous = None

        for value in ordered:
            if previous is None or value != previous:
                result.append(value)
                previous = value

        return result
