class RetrievalDocumentStore:
    """
    Deterministic source-document store used to rebuild retrieval vectors safely.

    Re-fitting IDF changes the vector space, so the retrieval service retains the
    document source needed for a complete rebuild instead of mixing stale and new
    embeddings.
    """

    def __init__(
        self,
        Document,
    ):
        self.Document = Document
        self._documents = {}
        self._order = []

    def from_payload(
        self,
        value,
    ):
        if isinstance(
            value,
            self.Document,
        ):
            return value

        if not isinstance(
            value,
            dict,
        ):
            raise TypeError(
                "document must be Document or dict"
            )

        for key in (
            "document_id",
            "text",
            "dataset_id",
        ):
            if key not in value:
                raise ValueError(
                    "document payload requires "
                    + key
                )

        labels = value.get(
            "labels",
            [],
        )

        if labels is None:
            labels = []

        return self.Document(
            document_id=value[
                "document_id"
            ],
            text=value[
                "text"
            ],
            dataset_id=value[
                "dataset_id"
            ],
            source_record_id=value.get(
                "source_record_id"
            ),
            metadata=value.get(
                "metadata",
                {},
            ),
            labels=list(
                labels
            ),
            split=value.get(
                "split",
                "unsplit",
            ),
            provenance=value.get(
                "provenance",
                {},
            ),
        )

    def replace_all(
        self,
        documents,
    ):
        staged = {}
        order = []

        for value in documents:
            document = self.from_payload(
                value
            )

            if document.document_id in staged:
                raise ValueError(
                    "duplicate document_id in replacement: "
                    + document.document_id
                )

            staged[
                document.document_id
            ] = document

            order.append(
                document.document_id
            )

        self._documents = staged
        self._order = order
        return self

    def upsert_many(
        self,
        documents,
    ):
        staged = []
        seen = {}

        for value in documents:
            document = self.from_payload(
                value
            )

            if document.document_id in seen:
                raise ValueError(
                    "duplicate document_id in upsert request: "
                    + document.document_id
                )

            seen[
                document.document_id
            ] = True

            staged.append(
                document
            )

        for document in staged:
            if (
                document.document_id
                not in self._documents
            ):
                self._order.append(
                    document.document_id
                )

            self._documents[
                document.document_id
            ] = document

        return self

    def remove(
        self,
        document_id,
    ):
        if not isinstance(
            document_id,
            str,
        ):
            raise TypeError(
                "document_id must be str"
            )

        if document_id not in self._documents:
            raise KeyError(
                "document not found: "
                + document_id
            )

        document = self._documents.pop(
            document_id
        )

        self._order = [
            item_id
            for item_id in self._order
            if item_id != document_id
        ]

        return document

    def get(
        self,
        document_id,
    ):
        if document_id not in self._documents:
            raise KeyError(
                "document not found: "
                + str(
                    document_id
                )
            )

        return self._documents[
            document_id
        ]

    def documents(
        self,
    ):
        return [
            self._documents[
                document_id
            ]
            for document_id in self._order
        ]

    def count(
        self,
    ):
        return len(
            self._order
        )

    def clear(
        self,
    ):
        self._documents = {}
        self._order = []
        return self

    def to_state(
        self,
    ):
        return [
            self._documents[
                document_id
            ].to_dict()
            for document_id in self._order
        ]

    def load_state(
        self,
        rows,
    ):
        if not isinstance(
            rows,
            list,
        ):
            raise TypeError(
                "document store state must be list"
            )

        return self.replace_all(
            rows
        )
