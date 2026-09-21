class PunctuationNormalizer:
    """
    Deterministic punctuation normalization.

    Only explicitly listed compatibility characters are mapped. This avoids
    silently changing language-specific punctuation that we do not understand.
    """

    def __init__(self):
        self._mapping = {
            "\u2018": "'",
            "\u2019": "'",
            "\u201A": "'",
            "\u201B": "'",
            "\u2032": "'",
            "\u201C": '"',
            "\u201D": '"',
            "\u201E": '"',
            "\u201F": '"',
            "\u2033": '"',
            "\u2010": "-",
            "\u2011": "-",
            "\u2012": "-",
            "\u2013": "-",
            "\u2014": "-",
            "\u2212": "-",
            "\u2026": "...",
            "\u00B7": ".",
            "\u2022": "*",
        }

    def normalize(self, text):
        if not isinstance(text, str):
            raise TypeError("text must be str")

        out = []
        i = 0

        while i < len(text):
            char = text[i]
            if char in self._mapping:
                out.append(self._mapping[char])
            else:
                out.append(char)
            i += 1

        return "".join(out)

    def mapping(self):
        result = {}
        for key in self._mapping:
            result[key] = self._mapping[key]
        return result
