class NormalizationResult:
    """
    Keeps the untouched source text alongside its normalized training form.
    """

    def __init__(self, original, normalized, history):
        self.original = original
        self.normalized = normalized
        self.history = history

    def changed(self):
        return self.original != self.normalized

    def to_dict(self):
        copied_history = []
        for item in self.history:
            copied = {}
            for key in item:
                copied[key] = item[key]
            copied_history.append(copied)

        return {
            "original": self.original,
            "normalized": self.normalized,
            "changed": self.changed(),
            "history": copied_history,
        }


class TextNormalizer:
    """
    Pipeline orchestrator for training-text normalization.

    Dependencies are injected so this module does not rely on import machinery.
    """

    def __init__(self, whitespace, punctuation, unicode_rules):
        if whitespace is None:
            raise ValueError("whitespace normalizer is required")
        if punctuation is None:
            raise ValueError("punctuation normalizer is required")
        if unicode_rules is None:
            raise ValueError("unicode rules are required")

        self.whitespace = whitespace
        self.punctuation = punctuation
        self.unicode_rules = unicode_rules

    def normalize(
        self,
        text,
        normalize_unicode=True,
        normalize_punctuation=True,
        normalize_whitespace=True,
        remove_controls=True,
        preserve_newlines=True,
    ):
        if not isinstance(text, str):
            raise TypeError("text must be str")

        self.unicode_rules.validate_scalar_values(text)

        original = text
        current = text
        history = []

        if normalize_unicode:
            before = current
            current = self.unicode_rules.normalize_compatibility(current)
            history.append(
                self._history_entry(
                    "unicode_compatibility",
                    before,
                    current,
                )
            )

        if remove_controls:
            before = current
            current = self.unicode_rules.remove_disallowed_controls(
                current,
                keep_newline=preserve_newlines,
                keep_tab=True,
            )
            history.append(
                self._history_entry(
                    "remove_disallowed_controls",
                    before,
                    current,
                )
            )

        if normalize_punctuation:
            before = current
            current = self.punctuation.normalize(current)
            history.append(
                self._history_entry(
                    "punctuation",
                    before,
                    current,
                )
            )

        if normalize_whitespace:
            before = current
            current = self.whitespace.normalize(
                current,
                collapse_spaces=True,
                trim_lines=True,
                collapse_blank_lines=True,
                preserve_newlines=preserve_newlines,
            )
            history.append(
                self._history_entry(
                    "whitespace",
                    before,
                    current,
                )
            )

        return NormalizationResult(
            original=original,
            normalized=current,
            history=history,
        )

    def _history_entry(self, name, before, after):
        return {
            "name": name,
            "changed": before != after,
            "input_length": len(before),
            "output_length": len(after),
        }
