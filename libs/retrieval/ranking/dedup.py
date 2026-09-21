class DuplicateSuppressor:
    """
    Conservative duplicate suppression for retrieval candidates.

    Duplicate identity can be established by:
      - exact normalized text
      - same document and exact source span
      - same item ID

    No fuzzy semantic claim is made here; MMR handles near-redundancy later.
    """

    def __init__(
        self,
        normalize_case=True,
        collapse_whitespace=True,
    ):
        self.normalize_case = bool(normalize_case)
        self.collapse_whitespace = bool(
            collapse_whitespace
        )

    def suppress(self, results):
        if not isinstance(results, (list, tuple)):
            results = list(results)

        kept = []
        seen_ids = {}
        seen_text = {}
        seen_spans = {}

        for result in results:
            entry = self._entry(result)

            if entry.item_id in seen_ids:
                continue

            text_key = self._text_key(
                entry.text
            )

            if text_key != "" and text_key in seen_text:
                continue

            span_key = self._span_key(
                entry
            )

            if span_key is not None and span_key in seen_spans:
                continue

            kept.append(result)
            seen_ids[entry.item_id] = True

            if text_key != "":
                seen_text[text_key] = True

            if span_key is not None:
                seen_spans[span_key] = True

        return kept

    def _entry(self, result):
        if hasattr(result, "entry"):
            return result.entry

        if hasattr(result, "item_id") and hasattr(result, "vector"):
            return result

        raise TypeError(
            "result must expose entry or be an index entry"
        )

    def _text_key(self, text):
        if not isinstance(text, str):
            return ""

        value = text

        if self.normalize_case:
            value = value.lower()

        if self.collapse_whitespace:
            pieces = []
            current = []
            index = 0

            while index < len(value):
                char = value[index]

                if char in (" ", "\t", "\n", "\r"):
                    if len(current) > 0:
                        pieces.append(
                            "".join(current)
                        )
                        current = []
                else:
                    current.append(char)

                index += 1

            if len(current) > 0:
                pieces.append(
                    "".join(current)
                )

            value = " ".join(pieces)

        return value

    def _span_key(self, entry):
        metadata = getattr(
            entry,
            "metadata",
            {},
        )

        if not isinstance(metadata, dict):
            return None

        start = None
        end = None

        if "char_start" in metadata and "char_end" in metadata:
            start = metadata["char_start"]
            end = metadata["char_end"]

        elif "token_start" in metadata and "token_end" in metadata:
            start = metadata["token_start"]
            end = metadata["token_end"]

        if start is None or end is None:
            return None

        return (
            entry.document_id,
            start,
            end,
        )
