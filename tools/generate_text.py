import argparse

from real_runtime import (
    ROOT,
    enter_project_root,
    load_inference_namespace,
)


def main():
    parser = argparse.ArgumentParser(
        description=(
            "Load a trained SireSoft-IKON-v1.0 checkpoint and perform real autoregressive generation."
        )
    )
    parser.add_argument(
        "prompt",
        nargs="?",
        default="SireSoft",
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
        "--max-new-tokens",
        type=int,
        default=32,
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
        "--top-k",
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
    args = parser.parse_args()

    enter_project_root()
    ns = load_inference_namespace()

    tokenizer_manager = ns[
        "build_tokenizer_manager"
    ]()
    tokenizer_manager.load_state_file(
        str(ROOT / args.tokenizer)
    )

    checkpoint = ROOT / args.checkpoint
    if not checkpoint.is_file():
        raise FileNotFoundError(
            "Missing trained checkpoint: "
            + str(checkpoint)
            + "\nRun: python tools/train_model.py"
        )

    registry = ns["ModelRegistry"]()
    registry.register_checkpoint(
        model_id="sirellm",
        version="1.0.0",
        checkpoint_path=str(checkpoint),
        metadata={
            "tokenizer_path": str(
                ROOT / args.tokenizer
            ),
        },
        stage=True,
    )
    registry.promote(
        "sirellm",
        "1.0.0",
    )

    runtime = ns[
        "InferenceRuntime"
    ](
        ns["ModelLoader"](
            registry=registry,
        )
    )

    info = runtime.load_active(
        "sirellm"
    )

    vocabulary = tokenizer_manager.model.vocabulary
    eos_id = vocabulary.special_id(
        "<EOS>"
    )
    pad_id = vocabulary.special_id(
        "<PAD>"
    )

    prompt_ids = tokenizer_manager.encode(
        args.prompt,
        add_bos=True,
        add_eos=False,
    )

    result = runtime.generate(
        prompt_ids=prompt_ids,
        max_new_tokens=args.max_new_tokens,
        eos_token_ids=[eos_id],
        sampler=args.sampler,
        seed=args.seed,
        temperature=args.temperature,
        top_k=args.top_k,
        top_p=args.top_p,
        repetition_penalty=1.05,
        banned_token_ids=[pad_id],
        allow_prompt_truncation=True,
    )

    text = tokenizer_manager.decode(
        result.generated_ids,
        skip_special=True,
    )

    print("Loaded:", info)
    print()
    print("PROMPT:")
    print(args.prompt)
    print()
    print("GENERATED:")
    print(text)
    print()
    print("tokens:", len(result.generated_ids))
    print("stop_reason:", result.stop_reason)


if __name__ == "__main__":
    main()
