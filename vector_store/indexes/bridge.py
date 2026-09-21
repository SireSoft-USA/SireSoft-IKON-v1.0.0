class RetrievalIndexBridge:
    """
    Integration bridge between RetrievalManager and generic vector-index store.

    It does not duplicate vectors or create a second embedding pipeline; it
    simply exposes the RetrievalManager's already-built FlatVectorIndex plus
    compatibility metadata.
    """

    def extract(
        self,
        retrieval_manager,
    ):
        if retrieval_manager is None:
            raise TypeError(
                "retrieval_manager is required"
            )

        if not hasattr(
            retrieval_manager,
            "index",
        ):
            raise TypeError(
                "retrieval_manager must expose index"
            )

        if not isinstance(
            retrieval_manager.index,
            FlatVectorIndex,
        ):
            raise TypeError(
                "retrieval_manager.index must be FlatVectorIndex"
            )

        if not hasattr(
            retrieval_manager,
            "status",
        ):
            raise TypeError(
                "retrieval_manager must provide status()"
            )

        if not hasattr(
            retrieval_manager,
            "tokenizer_signature",
        ):
            raise TypeError(
                "retrieval_manager must provide tokenizer_signature()"
            )

        status = (
            retrieval_manager
            .status()
        )

        return {
            "index": (
                retrieval_manager
                .index
            ),
            "metadata": {
                "source": (
                    "retrieval_manager"
                ),
                "documents": (
                    status.get(
                        "documents",
                        0,
                    )
                ),
                "chunks": (
                    status.get(
                        "chunks",
                        0,
                    )
                ),
                "tokenizer_signature": (
                    retrieval_manager
                    .tokenizer_signature()
                ),
                "dimension": (
                    status.get(
                        "dimension"
                    )
                ),
            },
        }
