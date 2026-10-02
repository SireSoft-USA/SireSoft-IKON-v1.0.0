import argparse
import json

from real_runtime import (
    ROOT,
    enter_project_root,
    load_retrieval_namespace,
)


def row_text(row):
    value = row.get("normalized_content")
    if isinstance(value, str) and value.strip():
        return value

    value = row.get("raw_content")
    if isinstance(value, str) and value.strip():
        return value

    conversation = row.get("conversation")
    if isinstance(conversation, dict):
        messages = conversation.get("messages")
        if isinstance(messages, list):
            pieces = []
            for message in messages:
                if not isinstance(message, dict):
                    continue
                content = message.get("content")
                if isinstance(content, str) and content:
                    pieces.append(content)
            if pieces:
                return "\n".join(pieces)

    return ""


def main():
    parser = argparse.ArgumentParser(
        description=(
            "Build and persist the real SireSoft retrieval index used by RAG."
        )
    )
    parser.add_argument(
        "--tokenizer",
        default=(
            "model_store/manifests/"
            "sirellm_tokenizer.sltok"
        ),
    )
    parser.add_argument(
        "--source",
        default=(
            "datasets/canonical/siresoft.jsonl"
        ),
    )
    parser.add_argument(
        "--output",
        default=(
            "vector_store/indexes/"
            "siresoft.slretr"
        ),
    )
    parser.add_argument(
        "--dimension",
        type=int,
        default=1024,
    )
    parser.add_argument(
        "--max-chars",
        type=int,
        default=1000,
    )
    parser.add_argument(
        "--overlap-chars",
        type=int,
        default=150,
    )
    args = parser.parse_args()

    enter_project_root()
    ns = load_retrieval_namespace()

    tokenizer_manager = ns[
        "build_tokenizer_manager"
    ]()

    tokenizer_manager.load_state_file(
        str(ROOT / args.tokenizer)
    )

    source_path = ROOT / args.source
    if not source_path.is_file():
        raise FileNotFoundError(
            "Missing canonical SireSoft file: "
            + str(source_path)
            + "\nRun: python tools/preprocess_all.py --datasets siresoft"
        )

    documents = []

    with source_path.open(
        "r",
        encoding="utf-8",
    ) as handle:
        for line in handle:
            line = line.strip()
            if not line:
                continue

            row = json.loads(line)
            text = row_text(row)
            if not text:
                continue

            metadata = row.get("metadata")
            if not isinstance(metadata, dict):
                metadata = {}

            if metadata.get(
                "training_eligible",
                True,
            ) is False:
                continue

            labels = row.get("labels")
            if not isinstance(labels, list):
                labels = []

            provenance = row.get("provenance")
            if not isinstance(provenance, dict):
                provenance = {}

            documents.append({
                "document_id": str(
                    row.get(
                        "record_id",
                        "siresoft-"
                        + str(len(documents)),
                    )
                ),
                "text": text,
                "dataset_id": "siresoft",
                "source_record_id": str(
                    row.get(
                        "record_id",
                        "siresoft-"
                        + str(len(documents)),
                    )
                ),
                "metadata": metadata,
                "labels": labels,
                "split": (
                    row.get("split")
                    if row.get("split")
                    in (
                        "train",
                        "validation",
                        "test",
                        "unsplit",
                    )
                    else "unsplit"
                ),
                "provenance": provenance,
            })

    if not documents:
        raise RuntimeError(
            "No SireSoft documents were available for retrieval indexing."
        )

    manager = ns[
        "RetrievalManager"
    ](
        tokenizer=tokenizer_manager.tokenizer,
        Document=ns["Document"],
        dimension=args.dimension,
        min_n=1,
        max_n=2,
        max_chars=args.max_chars,
        overlap_chars=args.overlap_chars,
    )

    print("SireSoft-IKON-v1.0 retrieval indexing")
    print("source documents:", len(documents))
    print("dimension:", args.dimension)
    print()

    manager.index_documents(
        documents,
        mode="replace",
        refit=True,
    )

    output_path = ROOT / args.output
    output_path.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    saved = manager.save_state(
        str(output_path)
    )

    status = manager.status()

    print("RETRIEVAL INDEX COMPLETE")
    print("documents:", status["documents"])
    print("chunks:", status["chunks"])
    print("index entries:", status["index_entries"])
    print("idf fitted:", status["idf_fitted"])
    print("artifact:", output_path)
    print("save info:", saved)


if __name__ == "__main__":
    main()
