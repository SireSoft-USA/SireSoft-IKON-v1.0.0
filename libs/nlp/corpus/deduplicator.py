class DuplicateGroup:
    """
    Describes duplicates without deleting provenance.

    The canonical record remains available elsewhere; this group only marks
    which corpus item is the representative and which IDs map to it.
    """

    def __init__(self, representative_id, fingerprint):
        self.representative_id = representative_id
        self.fingerprint = fingerprint
        self.duplicate_ids = []

    def add_duplicate(self, document_id):
        self.duplicate_ids.append(document_id)

    def duplicate_count(self):
        return len(self.duplicate_ids)

    def to_dict(self):
        return {
            "representative_id": self.representative_id,
            "fingerprint": self.fingerprint,
            "duplicate_ids": list(self.duplicate_ids),
        }


class DeduplicationResult:
    def __init__(self):
        self.unique_documents = []
        self.duplicate_groups = []
        self.document_to_representative = {}

    def unique_count(self):
        return len(self.unique_documents)

    def duplicate_count(self):
        total = 0
        for group in self.duplicate_groups:
            total += group.duplicate_count()
        return total

    def representative_for(self, document_id):
        return self.document_to_representative.get(document_id)


class Deduplicator:
    """
    Deterministic exact/normalized-text deduplicator.

    It does NOT delete source records. It returns:
      - unique_documents for model corpus construction
      - duplicate_groups preserving duplicate IDs/provenance mapping
    """

    def __init__(self, mode="exact", lowercase=False):
        if mode not in ("exact", "normalized"):
            raise ValueError("mode must be exact or normalized")
        self.mode = mode
        self.lowercase = lowercase

    def deduplicate(self, documents):
        result = DeduplicationResult()
        fingerprint_to_group = {}
        fingerprint_to_representative = {}

        for document in documents:
            if not hasattr(document, "document_id") or not hasattr(document, "text"):
                raise TypeError("document must provide document_id and text")

            comparable = self._comparable_text(document.text)
            fingerprint = self._fnv1a64_text(comparable)

            if fingerprint not in fingerprint_to_representative:
                result.unique_documents.append(document)
                fingerprint_to_representative[fingerprint] = document.document_id

                group = DuplicateGroup(
                    representative_id=document.document_id,
                    fingerprint=fingerprint,
                )
                fingerprint_to_group[fingerprint] = group
                result.document_to_representative[document.document_id] = document.document_id

            else:
                representative_id = fingerprint_to_representative[fingerprint]
                group = fingerprint_to_group[fingerprint]
                group.add_duplicate(document.document_id)
                result.document_to_representative[document.document_id] = representative_id

        for fingerprint in fingerprint_to_group:
            group = fingerprint_to_group[fingerprint]
            if group.duplicate_count() > 0:
                result.duplicate_groups.append(group)

        return result

    def _comparable_text(self, text):
        if not isinstance(text, str):
            raise TypeError("document text must be str")

        if self.mode == "exact":
            value = text
        else:
            value = self._basic_normalize(text)

        if self.lowercase:
            value = value.lower()

        return value

    def _basic_normalize(self, text):
        out = []
        previous_space = False

        i = 0
        while i < len(text):
            char = text[i]

            if char in (" ", "\t", "\n", "\r", "\v", "\f"):
                if not previous_space:
                    out.append(" ")
                previous_space = True
            else:
                out.append(char)
                previous_space = False

            i += 1

        start = 0
        end = len(out)

        while start < end and out[start] == " ":
            start += 1

        while end > start and out[end - 1] == " ":
            end -= 1

        return "".join(out[start:end])

    def _fnv1a64_text(self, text):
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
        i = 0

        while i < len(text):
            cp = ord(text[i])

            if cp <= 0x7F:
                values.append(cp)
            elif cp <= 0x7FF:
                values.append(0xC0 | (cp >> 6))
                values.append(0x80 | (cp & 0x3F))
            elif cp <= 0xFFFF:
                if 0xD800 <= cp <= 0xDFFF:
                    raise ValueError("isolated surrogate in document text")
                values.append(0xE0 | (cp >> 12))
                values.append(0x80 | ((cp >> 6) & 0x3F))
                values.append(0x80 | (cp & 0x3F))
            elif cp <= 0x10FFFF:
                values.append(0xF0 | (cp >> 18))
                values.append(0x80 | ((cp >> 12) & 0x3F))
                values.append(0x80 | ((cp >> 6) & 0x3F))
                values.append(0x80 | (cp & 0x3F))
            else:
                raise ValueError("invalid Unicode code point")

            i += 1

        return values
