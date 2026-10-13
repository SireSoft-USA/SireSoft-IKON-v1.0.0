"""One-command SireSoft-IKON developer/demo launcher.

Starts ONE Django application worker and the real React/Vite frontend; the
frontend reverse-proxies /api to the private Django listener. It does not train
or alter model artifacts. For managed production use Nginx + Gunicorn instead.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import signal
import shutil
import socket
import subprocess
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path

from tools.model_profiles import PROFILES, artifact_paths, get_profile

ROOT = Path(__file__).resolve().parent
FRONTEND = ROOT / "frontend"
CUDA_LIB = ROOT / "libs/core/gpu/libsireikon_cuda.so"
CUDA_SOURCE = ROOT / "libs/core/gpu/sireikon_cuda.cu"
CUDA_META = ROOT / "libs/core/gpu/libsireikon_cuda.build.json"
MODEL_ARTIFACTS = {
    "checkpoint": "model_store/checkpoints/sirellm-v1.lbckpt",
    "tokenizer": "model_store/manifests/sirellm_tokenizer.sltok",
    "retrieval index": "vector_store/indexes/siresoft.slretr",
}


def detect_cuda():
    """Check GPU accessibility and CUDA binary provenance without mutating drivers."""
    if sys.platform != "linux":
        return False, "The checked-in CUDA backend targets Linux; use CPU locally on Windows."
    if not CUDA_LIB.is_file() or not CUDA_META.is_file():
        return False, "Linux CUDA .so and/or build metadata missing (source-only package)."
    try:
        data = json.loads(CUDA_META.read_text(encoding="utf-8"))
        digest = hashlib.sha256(CUDA_SOURCE.read_bytes()).hexdigest()
        if data.get("source_sha256") != digest or data.get("architecture") != "sm_61":
            return False, "CUDA binary metadata doesn't match sm_61 source; deploy matching compiled binary."
        binary_hash = hashlib.sha256(CUDA_LIB.read_bytes()).hexdigest()
        if data.get("library_sha256") != binary_hash:
            return False, "CUDA .so checksum differs from build metadata. Use the verified Linux binary."
    except (OSError, ValueError) as exc:
        return False, f"Cannot validate CUDA metadata: {exc}"
    smi = shutil.which("nvidia-smi")
    if not smi:
        return False, "nvidia-smi not found; NVIDIA driver availability unknown."
    try:
        check = subprocess.run(
            [smi, "--query-gpu=name", "--format=csv,noheader"],
            stdout=subprocess.PIPE, stderr=subprocess.PIPE,
            text=True, timeout=12, check=False,
        )
    except (OSError, subprocess.TimeoutExpired) as exc:
        return False, f"NVIDIA driver diagnostic failed: {exc}"
    if check.returncode or not check.stdout.strip():
        return False, "NVIDIA driver unavailable: " + (check.stderr.strip() or "nvidia-smi failed")
    return True, check.stdout.strip().splitlines()[0]


def resolve_device(requested):
    if requested not in ("cpu", "auto", "cuda"):
        raise ValueError("Device must be cpu, cuda or auto")
    if requested == "cpu":
        return "cpu", "CPU selected explicitly."
    ok, why = detect_cuda()
    if ok:
        return "cuda", "GPU detected: " + why
    if requested == "cuda":
        raise RuntimeError("Strict CUDA requested; cannot start: " + why)
    return "cpu", "WARNING: GPU unavailable; using CPU. " + why


def artifact_status(profile_name="legacy"):
    return {
        name: path
        for name, relative in artifact_paths(profile_name).items()
        if not (path := (ROOT / relative)).is_file() or path.stat().st_size == 0
    }


def port_available(host, port):
    """Avoid accidentally starting a second Django/Vite on occupied ports."""
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        try:
            sock.bind((host, port))
            return True
        except OSError:
            return False


def terminate(proc):
    if proc is None or proc.poll() is not None:
        return
    proc.terminate()
    try:
        proc.wait(timeout=8)
    except subprocess.TimeoutExpired:
        proc.kill()
        proc.wait(timeout=3)


def http_ready(url):
    try:
        with urllib.request.urlopen(url, timeout=1.5) as response:
            return response.status == 200
    except (OSError, urllib.error.URLError, TimeoutError):
        return False


def await_frontend(frontend, backend, api_port, web_port, seconds=45):
    deadline = time.monotonic() + seconds
    while time.monotonic() < deadline:
        if frontend.poll() is not None:
            raise RuntimeError(f"React/Vite exited early with status {frontend.returncode}.")
        if backend.poll() is not None:
            raise RuntimeError(f"Django exited early with status {backend.returncode}.")
        if (http_ready(f"http://127.0.0.1:{api_port}/api/health")
                and http_ready(f"http://127.0.0.1:{web_port}/")):
            return
        time.sleep(0.4)
    raise RuntimeError("Timed out waiting for Django + React. Check process output above.")


def await_model(backend, api_port, seconds=120):
    """Wait for the real tokenizer, checkpoint and RAG index to be loaded."""
    import json
    deadline = time.monotonic() + seconds
    url = f"http://127.0.0.1:{api_port}/api/health"
    while time.monotonic() < deadline:
        if backend.poll() is not None:
            raise RuntimeError("Backend stopped while the trained model was loading")
        try:
            with urllib.request.urlopen(url, timeout=3) as response:
                health = json.loads(response.read().decode('utf-8'))
            if health.get("model_ready"):
                return health
            if health.get("model_error"):
                raise RuntimeError("Trained model loading failed: " + str(health["model_error"]))
        except (OSError, urllib.error.URLError, ValueError):
            pass
        time.sleep(1)
    raise RuntimeError("Timed out waiting for checkpoint/tokenizer/RAG to load")


def build_commands(args, npm):
    # Only one backend process/worker: each additional worker would duplicate
    # the model and GPU context. Keep Django on loopback; Vite proxies /api.
    if sys.platform.startswith("linux"):
        backend = [
            sys.executable, "-m", "gunicorn", "ikon_django.wsgi:application",
            "--config", "deploy/gunicorn.conf.py",
        ]
    else:
        backend = [
            sys.executable, str(ROOT / "manage.py"), "runserver", "--noreload",
            f"127.0.0.1:{args.api_port}",
        ]
    frontend = [
        npm, "run", "dev", "--", "--host", args.web_host,
        "--port", str(args.web_port), "--strictPort",
    ]
    return backend, frontend


def main(argv=None):
    parser = argparse.ArgumentParser(description="Start SireSoft-IKON as one application.")
    parser.add_argument("--model-profile", choices=tuple(PROFILES), default="legacy",
                        help="Use a matching trained checkpoint, tokenizer and retrieval index.")
    parser.add_argument("--device", choices=("auto", "cpu", "cuda"),
                        default=os.getenv("SIREIKON_DEVICE", "auto"))
    parser.add_argument("--gpu", action="store_true", help="Alias for --device cuda (strict, never silent CPU fallback).")
    parser.add_argument("--api-port", type=int, default=int(os.getenv("SIREIKON_API_PORT", "8000")))
    parser.add_argument("--web-port", type=int, default=int(os.getenv("SIREIKON_WEB_PORT", "5173")))
    parser.add_argument("--web-host", default=os.getenv("SIREIKON_WEB_HOST", "127.0.0.1"))
    parser.add_argument("--public-host", default=os.getenv("SIREIKON_PUBLIC_HOST", "localhost"))
    parser.add_argument("--model-timeout", type=int, default=300,
                        help="Seconds to wait for checkpoint/tokenizer/index initialization.")
    parser.add_argument("--require-model", action="store_true",
                        help="Refuse startup when tokenizer/checkpoint/retrieval index is missing.")
    parser.add_argument("--check", action="store_true", help="Only check CUDA/artifacts/ports, don't launch.")
    args = parser.parse_args(argv)
    if args.gpu:
        args.device = "cuda"
    if args.model_timeout < 1:
        parser.error("--model-timeout must be positive")
    if any(not 1 <= port <= 65535 for port in (args.api_port, args.web_port)):
        parser.error("Ports must be between 1 and 65535")
    if args.web_host not in ("127.0.0.1", "localhost", "0.0.0.0"):
        parser.error("--web-host must be 127.0.0.1, localhost or 0.0.0.0")
    try:
        device, diagnostic = resolve_device(args.device)
    except RuntimeError as exc:
        print("IKON GPU preflight failed:", exc, file=sys.stderr)
        return 2
    print("[IKON]", diagnostic, flush=True)
    profile = get_profile(args.model_profile)
    print(f"[IKON] Selected model profile: {profile.name}; expected context: {profile.sequence_length}", flush=True)
    missing = artifact_status(args.model_profile)
    if missing:
        print("[IKON] Model artifacts missing (generation unavailable until copied):", file=sys.stderr)
        for name, path in missing.items():
            print(f"  {name}: {path}", file=sys.stderr)
        if args.require_model:
            return 2
    else:
        print("[IKON] Checkpoint, tokenizer and RAG index found.", flush=True)
    if args.check:
        return 0

    if not port_available("127.0.0.1", args.api_port):
        print(f"[IKON] Backend port {args.api_port} is already in use. Choose --api-port.", file=sys.stderr)
        return 2
    if not port_available(args.web_host, args.web_port):
        print(f"[IKON] Frontend port {args.web_port} is already in use. Choose --web-port.", file=sys.stderr)
        return 2
    try:
        import django  # noqa: F401 - check current interpreter before any npm install
        if sys.platform == "linux":
            import gunicorn  # noqa: F401 - Gunicorn is required on Linux
    except ImportError as exc:
        print("[IKON] Django/Gunicorn missing from this Python environment. "
              "Run: python -m pip install -r requirements.txt", file=sys.stderr)
        print("[IKON] Missing package:", exc, file=sys.stderr)
        return 2
    npm = shutil.which("npm.cmd") or shutil.which("npm")
    if not npm:
        print("[IKON] npm is missing: install Node.js and npm.", file=sys.stderr)
        return 2
    if not (FRONTEND / "node_modules").is_dir():
        print("[IKON] Installing frontend dependencies with npm ci...", flush=True)
        try:
            subprocess.run([npm, "ci"], cwd=FRONTEND, check=True)
        except subprocess.CalledProcessError:
            print("[IKON] npm ci failed; frontend not started.", file=sys.stderr)
            return 2

    env = os.environ.copy()
    env["SIREIKON_DEVICE"] = device
    env["SIRELLM_TOKENIZER"] = str(ROOT / profile.tokenizer)
    env["SIRELLM_CHECKPOINT"] = str(ROOT / profile.checkpoint)
    env["SIRELLM_RETRIEVAL"] = str(ROOT / profile.retrieval)
    env.setdefault("SIRELLM_MAX_NEW_TOKENS", str(profile.max_new_tokens))
    env["SIREIKON_API_PORT"] = str(args.api_port)
    env["SIREIKON_BIND"] = f"127.0.0.1:{args.api_port}"
    env["DJANGO_ALLOWED_HOSTS"] = "127.0.0.1,localhost"
    # A development/demo launcher, not a service manager. Production should
    # supply a persistent secret and run managed Nginx/Gunicorn services.
    if not env.get("DJANGO_SECRET_KEY"):
        import secrets
        env["DJANGO_SECRET_KEY"] = secrets.token_urlsafe(48)
    if sys.platform != "linux":
        env.setdefault("SIREIKON_DEBUG", "1")
    backend_cmd, frontend_cmd = build_commands(args, npm)
    backend = frontend = None

    def stop_on_disconnect(signum, frame):
        # Clean up both child services if SSH drops (SIGHUP) or supervisor
        # stops the launcher (SIGTERM), avoiding orphaned 8010 listeners.
        raise KeyboardInterrupt

    if hasattr(signal, "SIGHUP"):
        signal.signal(signal.SIGHUP, stop_on_disconnect)
    signal.signal(signal.SIGTERM, stop_on_disconnect)
    try:
        backend = subprocess.Popen(backend_cmd, cwd=ROOT, env=env)
        frontend = subprocess.Popen(frontend_cmd, cwd=FRONTEND, env=env)
        await_frontend(frontend, backend, args.api_port, args.web_port)
        if not missing:
            print("[IKON] Waiting for trained LLM + RAG to load...", flush=True)
            health = await_model(backend, args.api_port, seconds=args.model_timeout)
            # Confirm the actual checkpoint architecture, not only filenames.
            health_url = f"http://127.0.0.1:{args.api_port}/v1/health"
            with urllib.request.urlopen(health_url, timeout=8) as response:
                model_health = json.loads(response.read().decode("utf-8"))
            reported = (model_health.get("model") or {}).get("model") or {}
            model_window = reported.get("max_seq_len")
            if model_window != profile.sequence_length:
                raise RuntimeError(
                    f"Profile {profile.name} expects {profile.sequence_length} context tokens; "
                    f"loaded checkpoint reports {model_window}. Do not rename legacy weights."
                )
            actual_device = health.get("compute", {}).get("active", "unknown")
            if device == "cuda" and actual_device != "cuda":
                raise RuntimeError("CUDA requested, but inference reported " + str(actual_device))
            print("[IKON] Model READY; active compute device:", actual_device, flush=True)
        print("\n" + "=" * 54, flush=True)
        print(f"  SireSoft-IKON: http://{args.public_host}:{args.web_port}", flush=True)
        print(f"  Engine: {device.upper()} | General chat + RAG selectable in Settings", flush=True)
        print("=" * 54 + "\n", flush=True)
        print("[IKON] Press Ctrl+C to stop both services. GPU/model status: use the /api/health endpoint.", flush=True)
        while backend.poll() is None and frontend.poll() is None:
            time.sleep(0.5)
        print("[IKON] A service stopped; shutting down the other.", file=sys.stderr)
        return 1
    except KeyboardInterrupt:
        print("\n[IKON] Stopping frontend and backend...", flush=True)
        return 0
    except (RuntimeError, OSError) as exc:
        print("[IKON] Launch failed:", exc, file=sys.stderr)
        return 1
    finally:
        terminate(frontend)
        terminate(backend)


if __name__ == "__main__":
    raise SystemExit(main())
