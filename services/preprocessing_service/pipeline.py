class PreprocessingResult:
    def __init__(
        self,
        dataset_id,
        records,
        documents,
        validation_issues,
        output_info=None,
    ):
        self.dataset_id = dataset_id
        self.records = list(records)
        self.documents = list(documents)
        self.validation_issues = list(
            validation_issues
        )
        self.output_info = output_info

    def valid(self):
        for issue in self.validation_issues:
            if issue.get("severity") == "error":
                return False

        return True

    def to_summary(self):
        error_count = 0
        warning_count = 0

        for issue in self.validation_issues:
            if issue.get("severity") == "error":
                error_count += 1
            elif issue.get("severity") == "warning":
                warning_count += 1

        return {
            "dataset_id": self.dataset_id,
            "record_count": len(self.records),
            "document_count": len(self.documents),
            "valid": self.valid(),
            "error_count": error_count,
            "warning_count": warning_count,
            "output": self.output_info,
        }


class PreprocessingPipeline:
    """
    raw -> parser -> adapter -> canonical -> normalize -> validate
        -> corpus Document -> optional canonical JSONL

    No record is silently dropped.
    """

    def __init__(
        self,
        loader,
        normalizer,
        validator,
        writer,
        Document,
    ):
        self.loader = loader
        self.normalizer = normalizer
        self.validator = validator
        self.writer = writer
        self.Document = Document

    def process(
        self,
        dataset_id,
        sources=None,
        normalize=True,
        strict=False,
        output_path=None,
    ):
        records = self.loader.load(
            dataset_id,
            sources=sources,
        )

        if normalize:
            records = self.normalizer.normalize_records(
                records
            )
        else:
            for record in records:
                record.add_preprocessing_step(
                    "text_normalization",
                    details={
                        "skipped": True,
                        "reason": "disabled_by_pipeline",
                    },
                )

        issues = []

        for record in records:
            validation = self.validator.validate_record(
                record
            )

            for issue in validation.issues:
                issues.append({
                    "record_id": getattr(
                        record,
                        "record_id",
                        None,
                    ),
                    "code": issue.code,
                    "message": issue.message,
                    "severity": issue.severity,
                    "field": issue.field,
                })

        unique_validation = (
            self.validator
            .validate_unique_record_ids(
                records
            )
        )

        for issue in unique_validation.issues:
            issues.append({
                "record_id": None,
                "code": issue.code,
                "message": issue.message,
                "severity": issue.severity,
                "field": issue.field,
            })

        if strict:
            for issue in issues:
                if issue["severity"] == "error":
                    raise ValueError(
                        "canonical validation failed: "
                        + issue["code"]
                        + ": "
                        + issue["message"]
                    )

        documents = []

        for record in records:
            if (
                record.metadata.get(
                    "training_eligible",
                    True,
                )
                is False
            ):
                continue

            documents.append(
                self.Document.from_canonical_record(
                    record
                )
            )

        output_info = None

        if output_path is not None:
            output_info = self.writer.write(
                records,
                output_path,
            )

        return PreprocessingResult(
            dataset_id=dataset_id,
            records=records,
            documents=documents,
            validation_issues=issues,
            output_info=output_info,
        )
