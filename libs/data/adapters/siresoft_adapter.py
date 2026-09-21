class SireSoftAdapter:
    """
    Loss-preserving adapter for SireSoft company knowledge.

    Important architectural rule:
    the source text is retained exactly in raw_content. Any later RAG chunking,
    normalization, embedding, or indexing happens in separate pipeline stages.
    """

    def __init__(self, CanonicalRecord):
        self.CanonicalRecord = CanonicalRecord

    def adapt_document(
        self,
        text,
        index=0,
        source_file="siresoft.txt",
        source_metadata=None,
    ):
        if not isinstance(text, str):
            raise TypeError("SireSoft document must be str")
        if not isinstance(index, int) or index < 0:
            raise ValueError("index must be non-negative int")
        if source_metadata is not None and not isinstance(source_metadata, dict):
            raise TypeError("source_metadata must be dict or None")

        metadata = {} if source_metadata is None else self._copy_dict(source_metadata)
        metadata["rag_eligible"] = True
        metadata["authoritative_company_source"] = True
        metadata["adapter"] = "SireSoftAdapter"

        return self.CanonicalRecord(
            record_id="siresoft-" + str(index),
            dataset_id="siresoft",
            dataset_name="SireSoft",
            source_file=source_file,
            source_record_index=index,
            source_format="txt",
            raw_content=text,
            normalized_content=text,
            original_fields={
                "text": text,
                "source_metadata": self._copy_dict(source_metadata),
            },
            labels=["company_knowledge", "rag_source"],
            language="en",
            document_type="company_document",
            source_type="company_knowledge",
            provenance={
                "dataset": "SireSoft",
                "source_file": source_file,
                "source_record_index": index,
            },
            split="unsplit",
            metadata=metadata,
        )

    def _copy_dict(self, value):
        if value is None:
            return {}
        out = {}
        for key in value:
            out[key] = value[key]
        return out
