"""Django HTTP endpoints; all LLM/CUDA/RAG work delegates to unchanged core."""
import json
import logging
from functools import wraps

from django.http import JsonResponse, StreamingHttpResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_GET, require_POST

from . import core

logger = logging.getLogger(__name__)
from .contracts import (
    PayloadError, parse_contract, FrontendChatRequest, ChatRequest,
    GenerateRequest, RetrieveRequest, EmbedRequest,
)

# Browser traffic should be same-origin via Vite/Nginx proxy; these are stateless
# JSON endpoints and do not use cookie authentication. If exposed publicly,
# restrict access at Nginx/VPN or add application authentication.

def _json_error(message, status=400):
    return JsonResponse({"detail": str(message)}, status=status)


def json_post(contract):
    def decorator(handler):
        @csrf_exempt
        @require_POST
        @wraps(handler)
        def wrapped(request):
            try:
                if request.content_type != 'application/json':
                    raise PayloadError("Content-Type must be application/json")
                payload = json.loads(request.body.decode('utf-8'))
                parsed = parse_contract(contract, payload)
            except (ValueError, UnicodeError, json.JSONDecodeError) as exc:
                return _json_error(exc)
            try:
                return handler(request, parsed)
            except core.StackUnavailable as exc:
                return _json_error(exc, 503)
            except Exception:
                logger.exception('IKON Django API request failed')
                # Do not leak tracebacks/model internals to unauthenticated callers.
                return _json_error("Model request failed; check the Django server logs", 500)
        return wrapped
    return decorator


@require_GET
def frontend_health(request):
    core.ensure_stack_loading()
    with core._stack_lock:
        ready = bool(core._stack["ready"])
        loading = bool(core._stack["loading"])
        error = core._stack["error"]
    return JsonResponse({
        "status": "ok", "backend": "online", "model_ready": ready,
        "model_loading": loading, "model_error": error,
    })


@json_post(FrontendChatRequest)
def frontend_chat_stream(request, payload):
    def events():
        try:
            result = (core._run_rag_frontend_chat(payload) if payload.use_rag
                      else core._run_base_frontend_chat(payload))
            yield core._ndjson_event({
                "type": "meta", "conversation_id": payload.conversation_id,
                "mode": "rag" if payload.use_rag else "base",
                "citations": result["citations"],
            })
            for chunk in core._stream_text_chunks(result["text"]):
                yield core._ndjson_event({"type": "token", "content": chunk})
            yield core._ndjson_event({
                "type": "meta", "conversation_id": payload.conversation_id,
                "done": True, "citations": result["citations"],
            })
        except core.StackUnavailable as exc:
            yield core._ndjson_event({"type": "error", "message": str(exc)})
        except Exception:
            logger.exception('IKON Django chat streaming failed')
            yield core._ndjson_event({"type": "error", "message": "Model generation failed"})
    return StreamingHttpResponse(events(), content_type="application/x-ndjson",
                                 headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"})


@require_GET
def health(request):
    core.ensure_stack_loading()
    with core._stack_lock:
        ready = bool(core._stack["ready"])
        loading = bool(core._stack["loading"])
        error = core._stack["error"]
        inference = core._stack["inference"]
        retrieval = core._stack["retrieval"]
    return JsonResponse({
        "status": "healthy" if ready else "degraded",
        "ready": ready, "loading": loading, "gateway": "online",
        "model": inference.status() if ready and inference is not None else None,
        "retrieval": retrieval.status() if ready and retrieval is not None else None,
        "error": error, "artifacts": core._artifact_paths(),
    })


@json_post(ChatRequest)
def chat(request, payload):
    stack = core._require_stack()
    eos, pad = core._special_token_ids(stack["tokenizer_manager"])
    result = stack["orchestrator"].answer(
        query_text=payload.query, max_new_tokens=payload.max_new_tokens,
        candidate_k=payload.candidate_k, top_k=payload.top_k,
        use_mmr=payload.use_mmr, mmr_lambda=payload.mmr_lambda,
        similarity_weight=payload.similarity_weight, eos_token_ids=[eos],
        sampler=payload.sampler, seed=payload.seed, temperature=payload.temperature,
        top_k_sampling=None, top_p=payload.top_p,
        repetition_penalty=payload.repetition_penalty, banned_token_ids=[pad],
    )
    data = result.to_dict()
    answer_text = data.get("answer_text", "")
    return JsonResponse({**data, "answer": answer_text,
                         "citations": core._frontend_citations(data.get("citations", []))})


@json_post(GenerateRequest)
def generate(request, payload):
    stack = core._require_stack()
    tokenizer = stack["tokenizer_manager"].tokenizer
    eos, pad = core._special_token_ids(stack["tokenizer_manager"])
    generated = stack["inference"].generate(
        prompt_ids=tokenizer.encode(payload.prompt),
        max_new_tokens=payload.max_new_tokens, eos_token_ids=[eos],
        sampler=payload.sampler, seed=payload.seed, temperature=payload.temperature,
        top_k=None, top_p=payload.top_p,
        repetition_penalty=payload.repetition_penalty, banned_token_ids=[pad],
        allow_prompt_truncation=True,
    )
    text = tokenizer.decode(generated.generated_ids)
    return JsonResponse({**generated.to_dict(), "generated_text": text, "answer": text})


@json_post(RetrieveRequest)
def retrieve(request, payload):
    stack = core._require_stack()
    result = stack["retrieval"].search(
        query=payload.query, top_k=payload.top_k,
        search_k=max(payload.candidate_k, payload.top_k),
        use_mmr=payload.use_mmr, mmr_lambda=payload.mmr_lambda,
        similarity_weight=payload.similarity_weight,
    )
    return JsonResponse(result.to_dict())


@json_post(EmbedRequest)
def embed(request, payload):
    stack = core._require_stack()
    embedding = stack["retrieval"].embedder.embed_text(payload.text)
    vector = list(embedding.vector)
    return JsonResponse({"text": payload.text, "dimension": len(vector), "vector": vector})
