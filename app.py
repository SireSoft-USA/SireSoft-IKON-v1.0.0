import json
import os
import re
import shutil
import subprocess
import sys
import threading
from contextlib import asynccontextmanager
from pathlib import Path
from types import SimpleNamespace
from typing import Any, Literal, Optional

try:
    from fastapi import FastAPI, HTTPException
    from fastapi.middleware.cors import CORSMiddleware
    from fastapi.responses import StreamingResponse
    from pydantic import BaseModel, Field
except ImportError as error:
    raise SystemExit(
        "FastAPI runtime is required. Install it once with:\n"
        "  pip install fastapi uvicorn"
    ) from error


ROOT = Path(__file__).resolve().parent
TOOLS_DIR = ROOT / "tools"
FRONTEND_DIR = ROOT / "frontend"

# tools/chat_rag.py imports real_runtime as a top-level module. Adding the
# existing tools directory to sys.path lets this FastAPI bridge reuse the
# project's existing SireLLM stack without modifying any backend source file.
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
# Request contracts
# ---------------------------------------------------------------------------


class FrontendMessage(BaseModel):
    role: Literal["system", "user", "assistant"]
    content: str


class FrontendChatRequest(BaseModel):
    conversation_id: str = Field(min_length=1)
    messages: list[FrontendMessage] = Field(min_length=1)
    use_rag: bool = True


class ChatRequest(BaseModel):
    query: str = Field(min_length=1)
    max_new_tokens: int = Field(default=64, ge=1, le=4096)
    candidate_k: int = Field(default=20, ge=1)
    top_k: int = Field(default=5, ge=1)
    use_mmr: bool = True
    mmr_lambda: float = Field(default=0.75, ge=0.0, le=1.0)
    similarity_weight: float = Field(default=1.0, ge=0.0)
    sampler: str = "greedy"
    seed: int = 1337
    temperature: float = Field(default=1.0, gt=0.0)
    top_p: Optional[float] = Field(default=None, gt=0.0, le=1.0)
    repetition_penalty: float = Field(default=1.05, gt=0.0)


class GenerateRequest(BaseModel):
    prompt: str = Field(min_length=1)
    max_new_tokens: int = Field(default=64, ge=1, le=4096)
    sampler: str = "greedy"
    seed: int = 1337
    temperature: float = Field(default=1.0, gt=0.0)
    top_p: Optional[float] = Field(default=None, gt=0.0, le=1.0)
    repetition_penalty: float = Field(default=1.05, gt=0.0)


class RetrieveRequest(BaseModel):
    query: str = Field(min_length=1)
    top_k: int = Field(default=5, ge=1)
    candidate_k: int = Field(default=20, ge=1)
    use_mmr: bool = True
    mmr_lambda: float = Field(default=0.75, ge=0.0, le=1.0)
    similarity_weight: float = Field(default=1.0, ge=0.0)


class EmbedRequest(BaseModel):
    text: str = Field(min_length=1)


# ---------------------------------------------------------------------------
# Existing SireLLM stack loader
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

        print("[SireLLM] tokenizer loaded")
        print("[SireLLM] checkpoint loaded")
        print("[SireLLM] retrieval index loaded")
        print("[SireLLM] RAG stack ready")

    except Exception as error:
        with _stack_lock:
            _stack["ready"] = False
            _stack["error"] = str(error)

        print("[SireLLM] model stack not ready:")
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
        raise HTTPException(
            status_code=503,
            detail="SireLLM model stack is still loading. Try again shortly.",
        )

    # If the generated artifacts were added after app.py was started, retry
    # loading them on the next request without requiring a process restart.
    _load_sirellm_stack()

    with _stack_lock:
        if _stack["ready"]:
            return _stack
        error = _stack["error"] or error

    raise HTTPException(
        status_code=503,
        detail=(
            "SireLLM model stack is not ready. "
            + (
                str(error)
                if error
                else "Required tokenizer/model/retrieval artifacts are unavailable."
            )
        ),
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
        "You are SireLLM, the SireSoft AI assistant.",
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


# ---------------------------------------------------------------------------
# FastAPI application
# ---------------------------------------------------------------------------


@asynccontextmanager
async def lifespan(_: FastAPI):
    _start_stack_loader()
    yield


app = FastAPI(
    title="SireLLM API",
    version="1.0.0",
    description=(
        "FastAPI bridge connecting the supplied React frontend to the existing "
        "SireLLM inference and RAG backend."
    ),
    lifespan=lifespan,
)

# The supplied Vite frontend proxies /api locally, so CORS is not required for
# normal development. These localhost origins also allow direct frontend-to-API
# access without touching the supplied frontend source.
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
        "http://127.0.0.1:5173",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ---------------------------------------------------------------------------
# Routes required by the supplied frontend.zip
# ---------------------------------------------------------------------------


@app.get("/api/health")
def frontend_health() -> dict[str, Any]:
    with _stack_lock:
        ready = bool(_stack["ready"])
        loading = bool(_stack["loading"])
        error = _stack["error"]

    # `status: ok` means the FastAPI bridge itself is reachable. Model readiness
    # is reported separately so the frontend/backend connection does not appear
    # offline merely because training artifacts are still being created.
    return {
        "status": "ok",
        "backend": "online",
        "model_ready": ready,
        "model_loading": loading,
        "model_error": error,
    }


@app.post("/api/chat/stream")
def frontend_chat_stream(request: FrontendChatRequest) -> StreamingResponse:
    def generate_events():
        try:
            result = (
                _run_rag_frontend_chat(request)
                if request.use_rag
                else _run_base_frontend_chat(request)
            )

            yield _ndjson_event(
                {
                    "type": "meta",
                    "conversation_id": request.conversation_id,
                    "mode": "rag" if request.use_rag else "base",
                    "citations": result["citations"],
                }
            )

            for piece in _stream_text_chunks(result["text"]):
                yield _ndjson_event(
                    {
                        "type": "token",
                        "content": piece,
                    }
                )

            yield _ndjson_event(
                {
                    "type": "meta",
                    "conversation_id": request.conversation_id,
                    "done": True,
                    "citations": result["citations"],
                }
            )

        except HTTPException as error:
            yield _ndjson_event(
                {
                    "type": "error",
                    "message": str(error.detail),
                }
            )
        except Exception as error:
            yield _ndjson_event(
                {
                    "type": "error",
                    "message": str(error),
                }
            )

    return StreamingResponse(
        generate_events(),
        media_type="application/x-ndjson",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",
        },
    )


# ---------------------------------------------------------------------------
# Existing /v1 API compatibility routes retained for the SireLLM architecture
# ---------------------------------------------------------------------------


@app.get("/v1/health")
def health() -> dict[str, Any]:
    with _stack_lock:
        ready = bool(_stack["ready"])
        loading = bool(_stack["loading"])
        error = _stack["error"]
        inference = _stack["inference"]
        retrieval = _stack["retrieval"]

    return {
        "status": "healthy" if ready else "degraded",
        "ready": ready,
        "loading": loading,
        "gateway": "online",
        "model": inference.status() if ready and inference is not None else None,
        "retrieval": retrieval.status() if ready and retrieval is not None else None,
        "error": error,
        "artifacts": _artifact_paths(),
    }


@app.post("/v1/chat")
def chat(request: ChatRequest) -> dict[str, Any]:
    stack = _require_stack()

    tokenizer_manager = stack["tokenizer_manager"]
    orchestrator = stack["orchestrator"]
    eos_id, pad_id = _special_token_ids(tokenizer_manager)

    try:
        result = orchestrator.answer(
            query_text=request.query,
            max_new_tokens=request.max_new_tokens,
            candidate_k=request.candidate_k,
            top_k=request.top_k,
            use_mmr=request.use_mmr,
            mmr_lambda=request.mmr_lambda,
            similarity_weight=request.similarity_weight,
            eos_token_ids=[eos_id],
            sampler=request.sampler,
            seed=request.seed,
            temperature=request.temperature,
            top_k_sampling=None,
            top_p=request.top_p,
            repetition_penalty=request.repetition_penalty,
            banned_token_ids=[pad_id],
        )
    except Exception as error:
        raise HTTPException(status_code=500, detail=str(error)) from error

    data = result.to_dict()
    answer_text = data.get("answer_text", "")
    citations = _frontend_citations(data.get("citations", []))

    return {
        **data,
        "answer": answer_text,
        "citations": citations,
    }


@app.post("/v1/generate")
def generate(request: GenerateRequest) -> dict[str, Any]:
    stack = _require_stack()

    tokenizer_manager = stack["tokenizer_manager"]
    inference = stack["inference"]
    tokenizer = tokenizer_manager.tokenizer
    eos_id, pad_id = _special_token_ids(tokenizer_manager)

    try:
        prompt_ids = tokenizer.encode(request.prompt)
        result = inference.generate(
            prompt_ids=prompt_ids,
            max_new_tokens=request.max_new_tokens,
            eos_token_ids=[eos_id],
            sampler=request.sampler,
            seed=request.seed,
            temperature=request.temperature,
            top_k=None,
            top_p=request.top_p,
            repetition_penalty=request.repetition_penalty,
            banned_token_ids=[pad_id],
            allow_prompt_truncation=True,
        )
        text = tokenizer.decode(result.generated_ids)
    except Exception as error:
        raise HTTPException(status_code=500, detail=str(error)) from error

    data = result.to_dict()
    return {
        **data,
        "generated_text": text,
        "answer": text,
    }


@app.post("/v1/retrieve")
def retrieve(request: RetrieveRequest) -> dict[str, Any]:
    stack = _require_stack()
    retrieval_manager = stack["retrieval"]

    try:
        result = retrieval_manager.search(
            query=request.query,
            top_k=request.top_k,
            search_k=max(request.candidate_k, request.top_k),
            use_mmr=request.use_mmr,
            mmr_lambda=request.mmr_lambda,
            similarity_weight=request.similarity_weight,
        )
    except Exception as error:
        raise HTTPException(status_code=500, detail=str(error)) from error

    return result.to_dict()


@app.post("/v1/embed")
def embed(request: EmbedRequest) -> dict[str, Any]:
    stack = _require_stack()
    retrieval_manager = stack["retrieval"]

    try:
        embedding = retrieval_manager.embedder.embed_text(request.text)
        vector = list(embedding.vector)
    except Exception as error:
        raise HTTPException(status_code=500, detail=str(error)) from error

    return {
        "text": request.text,
        "dimension": len(vector),
        "vector": vector,
    }


# ---------------------------------------------------------------------------
# One-command frontend + backend launcher
# ---------------------------------------------------------------------------


def _npm_executable() -> str:
    npm = shutil.which("npm.cmd") or shutil.which("npm")
    if npm is None:
        raise RuntimeError(
            "npm was not found. Install Node.js/npm before running app.py."
        )
    return npm


def _ensure_frontend_dependencies(npm: str) -> None:
    if (FRONTEND_DIR / "node_modules").is_dir():
        return

    print("[SireLLM] frontend dependencies are missing; running npm install...")
    result = subprocess.run(
        [npm, "install"],
        cwd=str(FRONTEND_DIR),
        check=False,
    )

    if result.returncode != 0:
        raise RuntimeError(
            "npm install failed. Run it manually inside the frontend folder."
        )


def _start_frontend() -> subprocess.Popen[Any]:
    if not FRONTEND_DIR.is_dir():
        raise RuntimeError(f"Frontend folder not found: {FRONTEND_DIR}")

    npm = _npm_executable()
    _ensure_frontend_dependencies(npm)

    print("[SireLLM] starting React frontend on http://localhost:5173")

    return subprocess.Popen(
        [npm, "run", "dev"],
        cwd=str(FRONTEND_DIR),
    )


def _stop_frontend(process: Optional[subprocess.Popen[Any]]) -> None:
    if process is None or process.poll() is not None:
        return

    try:
        if os.name == "nt":
            subprocess.run(
                [
                    "taskkill",
                    "/PID",
                    str(process.pid),
                    "/T",
                    "/F",
                ],
                check=False,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
            )
        else:
            process.terminate()
            process.wait(timeout=5)
    except Exception:
        try:
            process.kill()
        except Exception:
            pass


def main() -> None:
    try:
        import uvicorn
    except ImportError as error:
        raise SystemExit(
            "uvicorn is required. Install the FastAPI runtime with:\n"
            "  pip install fastapi uvicorn"
        ) from error

    frontend_process: Optional[subprocess.Popen[Any]] = None

    try:
        frontend_process = _start_frontend()

        print(f"[SireLLM] starting FastAPI backend on http://{HOST}:{PORT}")
        print("[SireLLM] frontend API: /api/chat/stream")
        print("[SireLLM] one command now runs both frontend and backend")

        uvicorn.run(
            app,
            host=HOST,
            port=PORT,
            log_level="info",
        )
    finally:
        _stop_frontend(frontend_process)


if __name__ == "__main__":
    main()
