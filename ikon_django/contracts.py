"""Standard-library JSON request schemas; no Pydantic/FastAPI dependency."""
from dataclasses import dataclass, fields, MISSING
from typing import Optional

class PayloadError(ValueError):
    pass

@dataclass
class FrontendMessage:
    role: str
    content: str

@dataclass
class FrontendChatRequest:
    conversation_id: str
    messages: list[FrontendMessage]
    use_rag: bool = True

@dataclass
class ChatRequest:
    query: str
    max_new_tokens: int = 64
    candidate_k: int = 20
    top_k: int = 5
    use_mmr: bool = True
    mmr_lambda: float = 0.75
    similarity_weight: float = 1.0
    sampler: str = "greedy"
    seed: int = 1337
    temperature: float = 1.0
    top_p: Optional[float] = None
    repetition_penalty: float = 1.05

@dataclass
class GenerateRequest:
    prompt: str
    max_new_tokens: int = 64
    sampler: str = "greedy"
    seed: int = 1337
    temperature: float = 1.0
    top_p: Optional[float] = None
    repetition_penalty: float = 1.05

@dataclass
class RetrieveRequest:
    query: str
    top_k: int = 5
    candidate_k: int = 20
    use_mmr: bool = True
    mmr_lambda: float = 0.75
    similarity_weight: float = 1.0

@dataclass
class EmbedRequest:
    text: str

_SCHEMA = {
    FrontendMessage: {"role": ("role",), "content": ("str",)},
    FrontendChatRequest: {"conversation_id": ("nonempty",), "messages": ("messages",), "use_rag": ("bool",)},
    ChatRequest: {
        "query": ("nonempty",), "max_new_tokens": ("int", 1, 4096),
        "candidate_k": ("int", 1, None), "top_k": ("int", 1, None),
        "use_mmr": ("bool",), "mmr_lambda": ("float", 0, 1, False),
        "similarity_weight": ("float", 0, None, False),
        "sampler": ("str",), "seed": ("int", None, None),
        "temperature": ("float", 0, None, True),
        "top_p": ("optional_float", 0, 1, True),
        "repetition_penalty": ("float", 0, None, True),
    },
    GenerateRequest: {
        "prompt": ("nonempty",), "max_new_tokens": ("int", 1, 4096),
        "sampler": ("str",), "seed": ("int", None, None),
        "temperature": ("float", 0, None, True),
        "top_p": ("optional_float", 0, 1, True),
        "repetition_penalty": ("float", 0, None, True),
    },
    RetrieveRequest: {
        "query": ("nonempty",), "top_k": ("int", 1, None),
        "candidate_k": ("int", 1, None), "use_mmr": ("bool",),
        "mmr_lambda": ("float", 0, 1, False),
        "similarity_weight": ("float", 0, None, False),
    },
    EmbedRequest: {"text": ("nonempty",)},
}

def parse_contract(model, payload):
    if not isinstance(payload, dict):
        raise PayloadError("Request JSON must be an object")
    values = {}
    for field in fields(model):
        key = field.name
        if key not in payload:
            if field.default is not MISSING:
                value = field.default
            else:
                raise PayloadError(f"Missing field: {key}")
        else:
            value = payload[key]
        rule = _SCHEMA[model][key]
        kind = rule[0]
        if kind == "messages":
            if not isinstance(value, list) or not value:
                raise PayloadError("messages must be a non-empty array")
            value = [parse_contract(FrontendMessage, item) for item in value]
        elif kind == "role":
            if value not in ("system", "user", "assistant"):
                raise PayloadError("role must be system, user, or assistant")
        elif kind in ("str", "nonempty"):
            if not isinstance(value, str) or (kind == "nonempty" and not value.strip()):
                raise PayloadError(f"{key} must be a non-empty string" if kind == "nonempty" else f"{key} must be a string")
        elif kind == "bool":
            if type(value) is not bool:
                raise PayloadError(f"{key} must be a boolean")
        elif kind == "int":
            if type(value) is not int or (rule[1] is not None and value < rule[1]) or (rule[2] is not None and value > rule[2]):
                raise PayloadError(f"{key} must be an integer in the allowed range")
        elif kind in ("float", "optional_float"):
            if value is None and kind == "optional_float":
                pass
            elif isinstance(value, bool) or not isinstance(value, (int, float)):
                raise PayloadError(f"{key} must be numeric")
            else:
                value = float(value)
                low, high, exclusive_low = rule[1:]
                if (low is not None and (value <= low if exclusive_low else value < low)) or (high is not None and value > high) or not __import__('math').isfinite(value):
                    raise PayloadError(f"{key} is outside its allowed range")
        values[key] = value
    return model(**values)
