class TinyStoriesAdapter:
    """
    Adapter for TinyStories plain-text samples.

    Story boundaries must be provided by the caller or a later preprocessing
    stage. This adapter never invents boundaries and never destroys text.
    """

    def __init__(self, CanonicalRecord):
        self.CanonicalRecord = CanonicalRecord

    def adapt_story(self, text, index, source_file="TinyStories-train.txt", metadata=None):
        if not isinstance(text, str):
            raise TypeError("story must be str")
        if not isinstance(index, int) or index < 0:
            raise ValueError("index must be non-negative int")
        if metadata is not None and not isinstance(metadata, dict):
            raise TypeError("metadata must be dict or None")

        source_metadata = {} if metadata is None else self._copy_dict(metadata)
        source_metadata["adapter"] = "TinyStoriesAdapter"

        return self.CanonicalRecord(
            record_id="tinystories-" + str(index),
            dataset_id="tinystories",
            dataset_name="TinyStories",
            source_file=source_file,
            source_record_index=index,
            source_format="txt",
            raw_content=text,
            normalized_content=text,
            original_fields={
                "story": text,
                "metadata": self._copy_dict(metadata),
            },
            labels=["story", "language_modeling"],
            language="en",
            document_type="story",
            source_type="public_dataset",
            provenance={
                "dataset": "TinyStories",
                "source_record_index": index,
            },
            split="unsplit",
            metadata=source_metadata,
        )

    def _copy_dict(self, value):
        if value is None:
            return {}
        out = {}
        for key in value:
            out[key] = value[key]
        return out
