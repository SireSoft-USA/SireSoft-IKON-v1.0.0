class CanonicalNormalizer:
    """
    Normalizes only model-facing canonical content.

    raw_content, original_fields and source conversation payloads are preserved.
    """

    def __init__(self, text_normalizer):
        if text_normalizer is None or not hasattr(
            text_normalizer,
            "normalize",
        ):
            raise TypeError(
                "text_normalizer must provide normalize()"
            )

        self.text_normalizer = text_normalizer

    def normalize_record(self, record):
        if record is None:
            raise ValueError("record is required")

        value = getattr(
            record,
            "normalized_content",
            None,
        )

        if value is None:
            record.add_preprocessing_step(
                "text_normalization",
                details={
                    "skipped": True,
                    "reason": "no normalized_content",
                },
            )

            return record

        result = self.text_normalizer.normalize(
            value,
            preserve_newlines=True,
        )

        record.normalized_content = result.normalized

        record.add_preprocessing_step(
            "text_normalization",
            details={
                "skipped": False,
                "changed": result.changed(),
                "history": result.history,
            },
        )

        return record

    def normalize_records(self, records):
        result = []

        for record in records:
            result.append(
                self.normalize_record(
                    record
                )
            )

        return result
