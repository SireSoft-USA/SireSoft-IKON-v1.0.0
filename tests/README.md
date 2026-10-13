# SireLLM Final Project Tests

This folder is the final repository-level validation layer.

Important: replace the previous `tests/` folder completely with this folder.
Do not merge old `repository_validator.py` or old manifest files into it.

## Commands

Repository-only diagnosis:

```bash
python tests/diagnose_repository.py
```

Final integration test:

```bash
python tests/test_system_integration.py
```

Curated cross-layer smoke suite:

```bash
python tests/run_all.py --smoke
```

All 116 mapped folder tests:

```bash
python tests/run_all.py --all
```

## Coverage model

Per-folder test coverage is no longer discovered with filesystem glob logic.
`system_manifest.py` contains an exact `TEST_FILE_BY_FOLDER` mapping for all
117 internal folders. This makes validation deterministic on Windows and
prevents false negatives for:

- `frontend/test_frontend_shell.py`
- `frontend/css/test_frontend_css.py`
- `frontend/js/test_frontend_js.py`
- `frontend/assets/test_frontend_assets.py`

The validator also avoids the regular-expression pattern that caused the
Python 3.10 `unterminated subpattern` error.

## Unified app regression and live end-to-end tests

The test runner now includes `tests/test_unified_app.py` (launcher and strict
CUDA fail-fast), `tests/test_compact_rag.py` (real short-window retrieval and
citation budgeting), and the existing Django/frontend tests. Both new unit
suites run without a trained checkpoint, driver or internet connection.

```bash
python -m pip install -r requirements.txt
python tools/run_tests.py --quick --require-django
python tools/run_tests.py --require-django
```

`tools/test_live_app.py` is **intentionally excluded from the automated
source suite**: it requires the real running application, trained artifacts
and real HTTP requests. After starting `python app.py`, test both real chat
modes through the frontend proxy:

```bash
python tools/test_live_app.py --web-url http://127.0.0.1:5173
# On the Quadro P5000 when nvidia-smi and the driver are working:
python tools/test_live_app.py --web-url http://127.0.0.1:5173 --require-gpu
```

The strict GPU live test fails if CUDA was not actually selected or no CUDA
kernels were recorded. It does not claim generated text is semantically good.
