"""Framework-independent adapter to SireSoft-IKON's existing CUDA/LLM/RAG runtime.

The original model loading, chat generation, retrieval, and streaming helpers
are preserved; Django only replaces the HTTP-facing FastAPI bridge.
"""
import json
import os
import re
import sys
import threading
from pathlib import Path
from types import SimpleNamespace
from typing import Any
from .contracts import FrontendMessage, FrontendChatRequest

class StackUnavailable(RuntimeError):
    pass

ROOT = Path(__file__).resolve().parents[1]
TOOLS_DIR = ROOT / "tools"
FRONTEND_DIR = ROOT / "frontend"

# tools/chat_rag.py imports real_runtime as a top-level module. Adding the
# existing tools directory to sys.path lets the Django API reuse the
# project's existing SireSoft-IKON-v1.0 stack without modifying any backend source file.
if str(TOOLS_DIR) not in sys.path:
    sys.path.insert(0, str(TOOLS_DIR))


DEFAULT_TOKENIZER = os.getenv(
    "SIRELLM_TOKENIZER",
    "model_store/manifests/sirellm_tokenizer.sltok",
)
DEFAULT_CHECKPOINT = os.getenv(
    "SIRELLM_CHECKPOINT",
    "model_store/checkpoints/sirellm-v1.lbckpt",
)
DEFAULT_RETRIEVAL = os.getenv(
    "SIRELLM_RETRIEVAL",
    "vector_store/indexes/siresoft.slretr",
)

HOST = os.getenv("SIRELLM_HOST", "127.0.0.1")
PORT = int(os.getenv("SIRELLM_PORT", "8000"))
DEFAULT_MAX_NEW_TOKENS = int(
    os.getenv("SIRELLM_MAX_NEW_TOKENS", "32")
)


# ---------------------------------------------------------------------------
# Existing SireSoft-IKON-v1.0 stack loader
# ---------------------------------------------------------------------------


_stack_lock = threading.Lock()
_stack: dict[str, Any] = {
    "namespace": None,
    "tokenizer_manager": None,
    "inference": None,
    "retrieval": None,
    "orchestrator": None,
    "loading": False,
    "ready": False,
    "error": None,
}


def _artifact_paths() -> dict[str, str]:
    return {
        "tokenizer": str(ROOT / DEFAULT_TOKENIZER),
        "checkpoint": str(ROOT / DEFAULT_CHECKPOINT),
        "retrieval": str(ROOT / DEFAULT_RETRIEVAL),
    }


def _load_sirellm_stack() -> None:
    with _stack_lock:
        if _stack["ready"] or _stack["loading"]:
            return
        _stack["loading"] = True
        _stack["error"] = None

    try:
        # This is the existing real runtime already used by tools/chat_rag.py.
        from chat_rag import build_stack

        args = SimpleNamespace(
            tokenizer=DEFAULT_TOKENIZER,
            checkpoint=DEFAULT_CHECKPOINT,
            retrieval=DEFAULT_RETRIEVAL,
            device=os.getenv("SIREIKON_DEVICE", "auto"),
            cuda_device_index=int(os.getenv("SIREIKON_CUDA_DEVICE", "0")),
        )

        (
            namespace,
            tokenizer_manager,
            inference,
            retrieval,
            orchestrator,
        ) = build_stack(args)

        with _stack_lock:
            _stack.update(
                {
                    "namespace": namespace,
                    "tokenizer_manager": tokenizer_manager,
                    "inference": inference,
                    "retrieval": retrieval,
                    "orchestrator": orchestrator,
                    "ready": True,
                    "error": None,
                }
            )

        print("[SireSoft-IKON-v1.0] tokenizer loaded")
        print("[SireSoft-IKON-v1.0] checkpoint loaded")
        print("[SireSoft-IKON-v1.0] retrieval index loaded")
        print("[SireSoft-IKON-v1.0] RAG stack ready")

    except Exception as error:
        with _stack_lock:
            _stack["ready"] = False
            _stack["error"] = str(error)

        print("[SireSoft-IKON-v1.0] model stack not ready:")
        print(str(error))

    finally:
        with _stack_lock:
            _stack["loading"] = False


def _start_stack_loader() -> None:
    thread = threading.Thread(
        target=_load_sirellm_stack,
        name="sirellm-stack-loader",
        daemon=True,
    )
    thread.start()


def _require_stack() -> dict[str, Any]:
    with _stack_lock:
        ready = bool(_stack["ready"])
        loading = bool(_stack["loading"])
        error = _stack["error"]

    if ready:
        return _stack

    if loading:
        raise StackUnavailable("SireSoft-IKON-v1.0 model stack is still loading. Try again shortly.")

    # If the generated artifacts were added after app.py was started, retry
    # loading them on the next request without requiring a process restart.
    _load_sirellm_stack()

    with _stack_lock:
        if _stack["ready"]:
            return _stack
        error = _stack["error"] or error

    raise StackUnavailable(
        "SireSoft-IKON-v1.0 model stack is not ready. "
        + (str(error) if error else "Required tokenizer/model/retrieval artifacts are unavailable.")
    )


def _special_token_ids(tokenizer_manager: Any) -> tuple[int, int]:
    vocabulary = tokenizer_manager.model.vocabulary
    eos_id = vocabulary.special_id("<EOS>")
    pad_id = vocabulary.special_id("<PAD>")
    return eos_id, pad_id


def _frontend_citations(
    citations: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    normalized = []

    for index, citation in enumerate(citations):
        document_id = citation.get("document_id")
        dataset_id = citation.get("dataset_id")
        marker = citation.get("marker") or f"S{index + 1}"

        normalized.append(
            {
                **citation,
                "id": citation.get("citation_id") or marker,
                "title": document_id or dataset_id or f"Source {index + 1}",
                "snippet": citation.get("text", ""),
            }
        )

    return normalized


# ---------------------------------------------------------------------------
# Frontend adapter helpers
# ---------------------------------------------------------------------------


def _latest_user_message(messages: list[FrontendMessage]) -> str:
    for message in reversed(messages):
        if message.role == "user" and message.content.strip():
            return message.content.strip()

    raise ValueError("Chat request requires at least one non-empty user message")


def _base_prompt(messages: list[FrontendMessage]) -> str:
    """Build a normal causal-chat prompt from the React chat history."""

    lines = [
        "<SYSTEM>",
        "You are SireSoft-IKON-v1.0, the SireSoft AI assistant.",
    ]

    for message in messages:
        content = message.content.strip()
        if not content:
            continue

        if message.role == "system":
            lines.extend(["<SYSTEM>", content])
        elif message.role == "user":
            lines.extend(["<USER>", content])
        elif message.role == "assistant":
            lines.extend(["<ASSISTANT>", content])

    lines.append("<ASSISTANT>")
    return "\n".join(lines)


def _run_rag_frontend_chat(request: FrontendChatRequest) -> dict[str, Any]:
    stack = _require_stack()
    query = _latest_user_message(request.messages)

    tokenizer_manager = stack["tokenizer_manager"]
    orchestrator = stack["orchestrator"]
    eos_id, pad_id = _special_token_ids(tokenizer_manager)

    result = orchestrator.answer(
        query_text=query,
        max_new_tokens=DEFAULT_MAX_NEW_TOKENS,
        candidate_k=20,
        top_k=5,
        use_mmr=True,
        mmr_lambda=0.75,
        similarity_weight=1.0,
        eos_token_ids=[eos_id],
        sampler="greedy",
        seed=1337,
        temperature=1.0,
        top_k_sampling=None,
        top_p=None,
        repetition_penalty=1.05,
        banned_token_ids=[pad_id],
    )

    data = result.to_dict()
    return {
        "text": data.get("answer_text", ""),
        "citations": _frontend_citations(data.get("citations", [])),
        "metadata": data,
    }


def _run_base_frontend_chat(request: FrontendChatRequest) -> dict[str, Any]:
    stack = _require_stack()

    tokenizer_manager = stack["tokenizer_manager"]
    inference = stack["inference"]
    tokenizer = tokenizer_manager.tokenizer
    eos_id, pad_id = _special_token_ids(tokenizer_manager)

    prompt = _base_prompt(request.messages)
    prompt_ids = tokenizer.encode(prompt)

    result = inference.generate(
        prompt_ids=prompt_ids,
        max_new_tokens=DEFAULT_MAX_NEW_TOKENS,
        eos_token_ids=[eos_id],
        sampler="greedy",
        seed=1337,
        temperature=1.0,
        top_k=None,
        top_p=None,
        repetition_penalty=1.05,
        banned_token_ids=[pad_id],
        allow_prompt_truncation=True,
    )

    text = tokenizer.decode(result.generated_ids)
    return {
        "text": text,
        "citations": [],
        "metadata": result.to_dict(),
    }


def _stream_text_chunks(text: str):
    # Preserve whitespace exactly while providing the incremental chunks the
    # supplied React frontend expects from /api/chat/stream.
    pieces = re.findall(r"\S+\s*|\s+", text)
    if not pieces and text:
        pieces = [text]
    return pieces


def _ndjson_event(event: dict[str, Any]) -> str:
    return json.dumps(event, ensure_ascii=False) + "\n"



# Start model loading lazily once a request reaches a web worker; never at
# Django import time, because management commands should not load the GPU.
_loader_started = False

def ensure_stack_loading():
    global _loader_started
    with _stack_lock:
        if _loader_started:
            return
        _loader_started = True
    _start_stack_loader()

