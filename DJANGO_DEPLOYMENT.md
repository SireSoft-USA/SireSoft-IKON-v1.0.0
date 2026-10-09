# SireSoft-IKON v1.0.0 — Django migration

## Architecture

**Nginx (port 8080) → Django/Gunicorn (127.0.0.1:8000) → existing IKON inference/RAG/CUDA code → existing stores.** The React/Vite frontend is **unchanged** except for replacing a FastAPI error label. Vite serves the frontend during development; Nginx serves the compiled frontend in production.

The Django project (`ikon_django/`) replaces the original FastAPI entry point in `app.py`. All ML code under `libs/`, `services/`, `runtime/`, `tools/`, `model_store/`, and `vector_store/` remains unchanged. The custom CUDA `.cu` and compiled-backend loading contracts are preserved. Django uses a default local SQLite metadata database (`ikon.sqlite3`) for optional future Django application models; **it does not migrate or replace IKON checkpoints, tokenizer files, or the custom retrieval index**. For PostgreSQL, configure `SIREIKON_DB_ENGINE=django.db.backends.postgresql` and the `SIREIKON_DB_*` variables with the PostgreSQL driver installed separately.

## Install and run locally

```bash
python -m venv .venv
source .venv/bin/activate       # Windows PowerShell: .venv\\Scripts\\Activate.ps1
python -m pip install -r requirements.txt
export SIREIKON_DEBUG=1         # Windows PowerShell: $env:SIREIKON_DEBUG="1"
python manage.py check
python manage.py runserver 127.0.0.1:8000
```

Then, in another terminal:

```bash
cd frontend
npm ci
npm run dev
```

Browse `http://localhost:5173`. The Vite `/api` proxy already targets port `8000`. Alternatively, run `python app.py` to launch both development processes (requires `npm`); it enables Django dev-mode automatically for that child process. `python run_pipeline.py` is **still the separate CUDA training pipeline**, unaffected by Django.

## Production deployment (Rocky Linux / Quadro P5000)

**Do not overwrite the existing trained artifacts.** The code-only ZIP intentionally excludes `datasets/`, `model_store` data, the retrieval index, `.venv`, `node_modules`, and the compiled `.so` binary. For GPU deployment, retain the existing `libs/core/gpu/libsireikon_cuda.so` and matching `.build.json` from the last successful CUDA build, or deliver those binary artifacts separately. This ZIP alone is *not* a complete runnable GPU model.

1. Back up current server-side code/configuration, stop the previous FastAPI/uvicorn service, and preserve the datasets, checkpoint, index, and CUDA binary. **Do not start the new Django backend on an occupied port.**
2. Install Django and Gunicorn into the existing virtual environment (no CUDA toolkit needed): `python -m pip install -r requirements.txt`.
3. Configure required production environment variables:
   ```bash
   export DJANGO_SECRET_KEY='REPLACE_WITH_A_LONG_RANDOM_SECRET'
   export DJANGO_ALLOWED_HOSTS='10.0.2.22,localhost,127.0.0.1'
   export SIREIKON_DEVICE=cuda       # Strict GPU inference, if desired
   export SIRELLM_CHECKPOINT='model_store/checkpoints/sirellm-v1.lbckpt'
   export SIRELLM_TOKENIZER='model_store/manifests/sirellm_tokenizer.sltok'
   export SIRELLM_RETRIEVAL='vector_store/indexes/siresoft.slretr'
   ```
   Set these via your service manager or a protected environment file, never commit secrets to Git.
4. Validate: `python manage.py check --deploy` (review recommendations); then start Django with `./deploy/start-django.sh`. This is a foreground process; use your server's supervisor/process manager to keep it running and restart it during rollout. `systemctl` is **not required**.
5. Build the unchanged frontend: `cd frontend && npm ci && npm run build`. Deploy the **contents** of `frontend/dist/` into `/var/www/siresoft-ikon/` (owned/readable by Nginx). Configure Nginx using `deploy/nginx-siresoft-ikon.conf` after verifying it doesn't conflict with the current live website, run `nginx -t`, then reload Nginx using your host's management method. Keep it behind your existing VPN/access control; no new public unauthenticated endpoint should be exposed.
6. Verify:
   ```bash
   curl http://127.0.0.1:8000/api/health
   curl http://127.0.0.1:8000/v1/health
   curl http://127.0.0.1:8080/api/health
   ```
   Expect backend `online`; model readiness is a separate field and may initially be `false` while artifacts load. Test a real chat request and confirm model readiness before releasing traffic.

**IMPORTANT:** Keep only **one Gunicorn worker** with the current in-process model cache. Multiple workers each initialize their own model and GPU state. Long responses use Django `StreamingHttpResponse` with NDJSON events compatible with the existing React client. The output is chunked *after* the model generates the complete reply, just like the original implementation; it is not GPU token-by-token streaming.

## Stable HTTP contracts

| Method | Path | Purpose |
|---|---|---|
| GET | `/api/health` | React backend/stack readiness |
| POST | `/api/chat/stream` | NDJSON `meta` / `token` / `meta` or `error` |
| GET | `/v1/health` | IKON health and artifact paths |
| POST | `/v1/chat` | LLM + RAG orchestration |
| POST | `/v1/generate` | Base LLM generation |
| POST | `/v1/retrieve` | Retrieval index search |
| POST | `/v1/embed` | Text embedding |

JSON payload field names and default generation/retrieval parameters are preserved. Django replaces Pydantic with standard-library dataclass-based validation, returning HTTP 400 on invalid JSON/fields, HTTP 503 when model artifacts are unavailable, and HTTP 500 on unexpected inference errors. CSRF is exempt **only for these stateless JSON POST endpoints** because they do not use session cookies; enforce access at the VPN/reverse-proxy layer before exposing publicly.

## Tests

```bash
python tests/test_django_contract.py
python tests/test_django_http.py
python tests/test_frontend_api.py
python tests/test_system_integration.py
python tools/run_tests.py --quick --require-django
python tools/run_tests.py --require-django
```

Django HTTP integration tests require Django; install requirements.txt before executing these checks. The pure-contract and source tests also run without Django. CUDA smoke test on the GPU server is unchanged:

```bash
python tools/test_gpu_training.py --arch sm_61 --require-cuda
```
