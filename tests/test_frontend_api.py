from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
API = ROOT / "frontend" / "src" / "lib" / "api.ts"
BACKEND = ROOT / "app.py"


def check(condition, message):
    if not condition:
        raise AssertionError(message)


def main():
    api = API.read_text(encoding="utf-8")
    backend = BACKEND.read_text(encoding="utf-8")

    check("/api/health" in api, "Frontend health endpoint missing")
    check("/api/chat/stream" in api, "Frontend streaming chat endpoint missing")
    check("fetch(" in api, "Frontend API client does not use fetch")
    check("TextDecoder" in api, "Streaming response decoder missing")
    check("/api/health" in backend, "FastAPI health route missing")
    check("/api/chat/stream" in backend, "FastAPI streaming route missing")

    print("FRONTEND API CONTRACT TEST: PASS")


if __name__ == "__main__":
    main()
