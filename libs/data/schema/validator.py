class ValidationIssue:
    def __init__(self, code, message, severity="error", field=None):
        if severity not in ("error", "warning"):
            raise ValueError("severity must be error or warning")
        self.code = code
        self.message = message
        self.severity = severity
        self.field = field

    def to_dict(self):
        return {
            "code": self.code,
            "message": self.message,
            "severity": self.severity,
            "field": self.field,
        }


class ValidationResult:
    def __init__(self):
        self.issues = []

    def add(self, issue):
        self.issues.append(issue)

    def is_valid(self):
        for issue in self.issues:
            if issue.severity == "error":
                return False
        return True

    def error_count(self):
        count = 0
        for issue in self.issues:
            if issue.severity == "error":
                count += 1
        return count

    def warning_count(self):
        count = 0
        for issue in self.issues:
            if issue.severity == "warning":
                count += 1
        return count


class SchemaValidator:
    """
    Structural validation for canonical records before they enter the unified
    corpus. Dataset-specific semantic checks will live in adapter/services.
    """

    VALID_FORMATS = (
        "json",
        "jsonl",
        "txt",
        "csv",
        "xml",
        "html",
        "binary",
        "unknown",
    )

    VALID_SPLITS = (
        None,
        "train",
        "validation",
        "test",
        "unsplit",
    )

    def validate_message(self, message):
        result = ValidationResult()

        if not hasattr(message, "role"):
            result.add(ValidationIssue("MSG_ROLE_MISSING", "message role is missing", field="role"))
        elif message.role not in ("system", "user", "assistant", "tool", "unknown"):
            result.add(ValidationIssue("MSG_ROLE_INVALID", "message role is invalid", field="role"))

        if not hasattr(message, "content"):
            result.add(ValidationIssue("MSG_CONTENT_MISSING", "message content is missing", field="content"))
        elif not isinstance(message.content, str):
            result.add(ValidationIssue("MSG_CONTENT_TYPE", "message content must be str", field="content"))
        elif message.content == "":
            result.add(ValidationIssue("MSG_CONTENT_EMPTY", "message content is empty", severity="warning", field="content"))

        return result

    def validate_conversation(self, conversation):
        result = ValidationResult()

        if not hasattr(conversation, "messages"):
            result.add(ValidationIssue("CONV_MESSAGES_MISSING", "conversation has no messages()", field="messages"))
            return result

        messages = conversation.messages()

        if len(messages) == 0:
            result.add(ValidationIssue("CONV_EMPTY", "conversation contains no messages", severity="warning"))

        i = 0
        while i < len(messages):
            child = self.validate_message(messages[i])
            for issue in child.issues:
                result.add(
                    ValidationIssue(
                        issue.code,
                        "message " + str(i) + ": " + issue.message,
                        issue.severity,
                        issue.field,
                    )
                )
            i += 1

        return result

    def validate_record(self, record):
        result = ValidationResult()

        required_strings = (
            "record_id",
            "dataset_id",
            "dataset_name",
            "source_file",
            "source_format",
        )

        for field in required_strings:
            if not hasattr(record, field):
                result.add(ValidationIssue("FIELD_MISSING", field + " is missing", field=field))
            else:
                value = getattr(record, field)
                if not isinstance(value, str):
                    result.add(ValidationIssue("FIELD_TYPE", field + " must be str", field=field))
                elif value == "":
                    result.add(ValidationIssue("FIELD_EMPTY", field + " must not be empty", field=field))

        if hasattr(record, "source_record_index"):
            value = record.source_record_index
            if not isinstance(value, int) or value < 0:
                result.add(ValidationIssue(
                    "SOURCE_INDEX_INVALID",
                    "source_record_index must be non-negative int",
                    field="source_record_index",
                ))
        else:
            result.add(ValidationIssue(
                "SOURCE_INDEX_MISSING",
                "source_record_index is missing",
                field="source_record_index",
            ))

        if hasattr(record, "source_format"):
            if record.source_format not in self.VALID_FORMATS:
                result.add(ValidationIssue(
                    "SOURCE_FORMAT_UNKNOWN",
                    "source_format is not registered",
                    severity="warning",
                    field="source_format",
                ))

        if hasattr(record, "split") and record.split not in self.VALID_SPLITS:
            result.add(ValidationIssue("SPLIT_INVALID", "invalid split", field="split"))

        has_source = False
        if hasattr(record, "raw_content") and record.raw_content is not None:
            has_source = True
        if hasattr(record, "original_fields") and len(record.original_fields) > 0:
            has_source = True
        if hasattr(record, "conversation") and record.conversation is not None:
            has_source = True

        if not has_source:
            result.add(ValidationIssue(
                "SOURCE_PAYLOAD_EMPTY",
                "record contains no preserved source payload",
                severity="warning",
            ))

        if hasattr(record, "conversation") and record.conversation is not None:
            child = self.validate_conversation(record.conversation)
            for issue in child.issues:
                result.add(issue)

        return result

    def validate_unique_record_ids(self, records):
        result = ValidationResult()
        seen = {}

        for record in records:
            if not hasattr(record, "record_id"):
                result.add(ValidationIssue("RECORD_ID_MISSING", "record_id is missing"))
                continue

            record_id = record.record_id
            if record_id in seen:
                result.add(ValidationIssue(
                    "RECORD_ID_DUPLICATE",
                    "duplicate record_id: " + str(record_id),
                    field="record_id",
                ))
            else:
                seen[record_id] = True

        return result
