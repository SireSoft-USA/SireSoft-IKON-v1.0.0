import argparse
from pathlib import Path

from real_runtime import (
    ROOT,
    enter_project_root,
    load_preprocessing_namespace,
)


DATASETS = (
    "dailydialog",
    "dolly",
    "movie-corpus",
    "siresoft",
    "tinystories",
    "openassistant",
)


def main():
    parser = argparse.ArgumentParser(
        description=(
            "Run SireLLM's real raw -> canonical preprocessing pipeline."
        )
    )
    parser.add_argument(
        "--datasets",
        nargs="*",
        default=list(DATASETS),
        choices=DATASETS,
        help="Dataset IDs to preprocess. Default: all six.",
    )
    parser.add_argument(
        "--strict",
        action="store_true",
        help="Fail immediately on canonical validation errors.",
    )
    parser.add_argument(
        "--force",
        action="store_true",
        help=(
            "Reprocess datasets even when a non-empty canonical "
            "output already exists."
        ),
    )
    args = parser.parse_args()

    enter_project_root()
    ns = load_preprocessing_namespace()
    pipeline = ns[
        "build_default_preprocessing_pipeline"
    ]()

    output_dir = ROOT / "datasets" / "canonical"
    output_dir.mkdir(
        parents=True,
        exist_ok=True,
    )

    print("SireLLM preprocessing")
    print("Project:", ROOT)
    print("Output:", output_dir)
    print()

    total_records = 0
    total_documents = 0
    total_errors = 0
    total_warnings = 0
    skipped = 0
    processed = 0

    for dataset_id in args.datasets:
        output_path = (
            output_dir
            / (dataset_id + ".jsonl")
        )

        if (
            not args.force
            and output_path.is_file()
            and output_path.stat().st_size > 0
        ):
            skipped += 1

            print(
                "[SKIP ]",
                dataset_id,
                "existing canonical output",
            )
            print(
                "       ->",
                output_path,
            )
            print()
            continue

        print("[START]", dataset_id)

        result = pipeline.process(
            dataset_id=dataset_id,
            normalize=True,
            strict=args.strict,
            output_path=str(output_path),
        )

        summary = result.to_summary()

        processed += 1

        total_records += summary[
            "record_count"
        ]
        total_documents += summary[
            "document_count"
        ]
        total_errors += summary[
            "error_count"
        ]
        total_warnings += summary[
            "warning_count"
        ]

        print(
            "[DONE ]",
            dataset_id,
            "records=",
            summary["record_count"],
            "documents=",
            summary["document_count"],
            "errors=",
            summary["error_count"],
            "warnings=",
            summary["warning_count"],
        )
        print("       ->", output_path)
        print()

        del result

    print("PREPROCESSING COMPLETE")
    print("processed datasets:", processed)
    print("skipped existing:", skipped)
    print("records:", total_records)
    print("training documents:", total_documents)
    print("validation errors:", total_errors)
    print("validation warnings:", total_warnings)

    if total_errors:
        print(
            "NOTE: canonical files were written, but validation errors exist. "
            "Re-run with --strict after correcting source issues."
        )


if __name__ == "__main__":
    main()
