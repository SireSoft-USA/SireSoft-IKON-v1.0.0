import argparse

from real_runtime import (
    ROOT,
    enter_project_root,
    load_rag_namespace,
)


def build_stack(args):
    ns = load_rag_namespace()

    compute_backend = ns.get("GPU_BACKEND")
    if compute_backend is not None:
        compute_backend.configure(
            getattr(args, "device", "auto"),
            getattr(args, "cuda_device_index", 0),
            strict=(getattr(args, "device", "auto") == "cuda"),
        )

    tokenizer_manager = ns[
        "build_tokenizer_manager"
    ]()
    tokenizer_manager.load_state_file(
        str(ROOT / args.tokenizer)
    )

    checkpoint = ROOT / args.checkpoint
    retrieval_path = ROOT / args.retrieval

    if not checkpoint.is_file():
        raise FileNotFoundError(
            "Missing checkpoint: "
            + str(checkpoint)
            + "\nRun: python tools/train_model.py"
        )

    if not retrieval_path.is_file():
        raise FileNotFoundError(
            "Missing retrieval index: "
            + str(retrieval_path)
            + "\nRun: python tools/build_retrieval.py"
        )

    registry = ns["ModelRegistry"]()
    registry.register_checkpoint(
        model_id="sirellm",
        version="1.0.0",
        checkpoint_path=str(checkpoint),
        stage=True,
    )
    registry.promote(
        "sirellm",
        "1.0.0",
    )

    inference = ns[
        "InferenceRuntime"
    ](
        ns["ModelLoader"](
            registry=registry,
        )
    )
    inference.load_active(
        "sirellm"
    )

    retrieval = ns[
        "RetrievalManager"
    ](
        tokenizer=(
            tokenizer_manager.tokenizer
        ),
        Document=ns["Document"],
        dimension=1024,
        min_n=1,
        max_n=2,
        max_chars=1000,
        overlap_chars=150,
    )
    retrieval.load_state_file(
        str(retrieval_path)
    )

    orchestrator = ns[
        "build_rag_orchestrator"
    ](
        tokenizer=(
            tokenizer_manager.tokenizer
        ),
        retrieval_manager=retrieval,
        inference_runtime=inference,
        max_context_tokens=512,
    )

    return (
        ns,
        tokenizer_manager,
        inference,
        retrieval,
        orchestrator,
    )


def answer(
    tokenizer_manager,
    orchestrator,
    query,
    args,
):
    vocabulary = (
        tokenizer_manager
        .model
        .vocabulary
    )

    eos_id = vocabulary.special_id(
        "<EOS>"
    )
    pad_id = vocabulary.special_id(
        "<PAD>"
    )

    result = orchestrator.answer(
        query_text=query,
        max_new_tokens=(
            args.max_new_tokens
        ),
        candidate_k=args.candidate_k,
        top_k=args.top_k,
        use_mmr=True,
        mmr_lambda=0.75,
        similarity_weight=1.0,
        eos_token_ids=[eos_id],
        sampler=args.sampler,
        seed=args.seed,
        temperature=args.temperature,
        top_k_sampling=(
            args.top_k_sampling
        ),
        top_p=args.top_p,
        repetition_penalty=1.05,
        banned_token_ids=[pad_id],
    )

    return result


def print_result(result):
    data = result.to_dict()

    if data["status"] != "ok":
        print(
            "[BLOCKED] phase=",
            data.get("blocked_phase"),
        )
        return

    print()
    print("SireSoft-IKON-v1.0:")
    print(data["answer_text"])

    citations = data.get(
        "citations",
        [],
    )

    if citations:
        print()
        print("Sources:")
        for citation in citations:
            marker = citation.get(
                "marker",
                "",
            )
            source = (
                citation.get(
                    "document_id"
                )
                or citation.get(
                    "source_record_id"
                )
                or "source"
            )
            print(
                " ",
                marker,
                source,
            )

    print()
    print(
        "generated_tokens=",
        data["generated_count"],
        "stop=",
        data["stop_reason"],
        "prompt_tokens=",
        data["prompt_token_count"],
        "context_tokens=",
        data["context_token_count"],
    )


def main():
    parser = argparse.ArgumentParser(
        description=(
            "Run the real trained SireSoft-IKON-v1.0 + SireSoft RAG stack as an interactive CLI."
        )
    )
    parser.add_argument(
        "query",
        nargs="?",
        default=None,
    )
    parser.add_argument(
        "--tokenizer",
        default=(
            "model_store/manifests/"
            "sirellm_tokenizer.sltok"
        ),
    )
    parser.add_argument(
        "--checkpoint",
        default=(
            "model_store/checkpoints/"
            "sirellm-v1.lbckpt"
        ),
    )
    parser.add_argument(
        "--retrieval",
        default=(
            "vector_store/indexes/"
            "siresoft.slretr"
        ),
    )
    parser.add_argument(
        "--max-new-tokens",
        type=int,
        default=16,
    )
    parser.add_argument(
        "--candidate-k",
        type=int,
        default=20,
    )
    parser.add_argument(
        "--top-k",
        type=int,
        default=3,
    )
    parser.add_argument(
        "--sampler",
        choices=(
            "greedy",
            "categorical",
        ),
        default="greedy",
    )
    parser.add_argument(
        "--temperature",
        type=float,
        default=1.0,
    )
    parser.add_argument(
        "--top-k-sampling",
        type=int,
        default=None,
    )
    parser.add_argument(
        "--top-p",
        type=float,
        default=None,
    )
    parser.add_argument(
        "--seed",
        type=int,
        default=1337,
    )
    parser.add_argument(
        "--device",
        choices=("auto", "cpu", "cuda"),
        default="auto",
    )
    parser.add_argument(
        "--cuda-device-index",
        type=int,
        default=0,
    )
    args = parser.parse_args()

    enter_project_root()

    (
        _,
        tokenizer_manager,
        inference,
        retrieval,
        orchestrator,
    ) = build_stack(args)

    print("SireSoft-IKON-v1.0 RAG READY")
    print("model:", inference.status())
    print("retrieval:", retrieval.status())
    print()

    if args.query is not None:
        result = answer(
            tokenizer_manager,
            orchestrator,
            args.query,
            args,
        )
        print_result(result)
        return

    print("Type /exit to stop.")

    while True:
        query = input("You: ").strip()

        if query.lower() in (
            "/exit",
            "/quit",
            "exit",
            "quit",
        ):
            break

        if not query:
            continue

        try:
            result = answer(
                tokenizer_manager,
                orchestrator,
                query,
                args,
            )
            print_result(result)
        except Exception as error:
            print(
                "SireSoft-IKON-v1.0 error:",
                error,
            )


if __name__ == "__main__":
    main()
